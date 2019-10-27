import os
import time
import datetime
import operator
import logging

from webhookHandler import send
import config
import jiraHandler


logging.basicConfig(filename="slackbot.log", level=logging.INFO, format='%(asctime)s : %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)


def createReport(persons):

	jira_report = {}

	for person in persons:
		weekday = datetime.datetime.today().weekday()
		if weekday: # not monday
			two_days_ago = (datetime.datetime.today() - datetime.timedelta(days=2)).strftime("%Y/%m/%d")
			today = datetime.datetime.today().strftime("%Y/%m/%d")
			jql = "worklogDate >= \'{}\' and worklogDate <= \'{}\' and worklogAuthor = \'{}\'".format(two_days_ago, today, person)
			work_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y/%m/%d")
			jira_report[person] = jiraHandler.getDayWorkLog(jql, work_date, work_date, person)
		else: # monday, we take holidays to log
			four_days_ago = (datetime.datetime.today() - datetime.timedelta(days=4)).strftime("%Y/%m/%d")
			today = datetime.datetime.today().strftime("%Y/%m/%d")
			jql = "worklogDate >= \'{}\' and worklogDate <= \'{}\' and worklogAuthor = \'{}\'".format(four_days_ago, today, person)
			work_date = (datetime.datetime.today() - datetime.timedelta(days=3)).strftime("%Y/%m/%d")
			yesterday = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y/%m/%d")
			jira_report[person] = jiraHandler.getDayWorkLog(jql, work_date, yesterday, person)


	slack_report = []

	for person in persons:
		jira_report[person] = sorted(jira_report[person].items(), key=operator.itemgetter(0))
		slack_report.append(createPersonJson(person, jira_report[person]))

	report = {}
	slack_report[0]['pretext'] = "*Work date: {}*".format(work_date)
	report["attachments"] = slack_report

	return report


def createPersonJson(person, person_report):
	report = {}
	report["title"] = person
	tickets = []
	total_time = 0
	if person_report:
		for time in person_report:
			for time_dict in time[1]:
				if time_dict['parent_key'] and time_dict['comment']:
					message = "Parent task: [{}] {}\nTime: {}\nLogged time: {}\nComment: {}".format(time_dict['parent_key'], time_dict['parent_summary'], time[0], time_dict['timeSpent'], time_dict['comment'])
				elif time_dict['parent_key']:
					message = "Parent task: [{}] {}\nTime: {}\nLogged time: {}".format(time_dict['parent_key'], time_dict['parent_summary'], time[0], time_dict['timeSpent'])
				elif time_dict['comment']:
					message = "Time: {}\nLogged time: {}\nComment: {}".format(time[0], time_dict['timeSpent'], time_dict['comment'])
				else:
					message = "Time: {}\nLogged time: {}".format(time[0], time_dict['timeSpent'])
				tickets.append({"title": "[{}] {}".format(time_dict['key'], time_dict['summary']) , "value": message, "short": False})
				total_time += time_dict['timeSpentSeconds']
		tickets.append({"title": "Total time: {}".format(str(datetime.timedelta(seconds=total_time))), "short": False})
	if total_time >= 25200: # 7h
		report["color"] = "good"
	elif total_time:
		report["color"] = "warning"
	else:
		report["color"] = "danger"
		tickets.append({"title": "No logged time", "short": False})
	report["fields"] = tickets
	report["footer"] = "Jira API"
	report["footer_icon"] = "https://platform.slack-edge.com/img/default_application_icon.png"

	return report


def monitoring():

	logger.info("Bot started")
	report = {}
	report["attachments"] = [{'text': "QA/Dev Worklog bot was started!"}]
	send(config.webhook_test, payload=report)

	while True:
		try:
			weekday = datetime.datetime.today().weekday()
			now = datetime.datetime.now()
			if weekday in range(0, 4) and now.hour == 6 and now.minute == 30:
				logger.info("Sending message")
				qa_response = send(config.webhook_qa, payload=createReport(config.qa))
				dev_response = send(config.webhook_dev, payload=createReport(config.dev))
				logger.info("Response: {} & {}".format(qa_response, dev_response))
				time.sleep(60)
			if now.hour in (8, 10, 12, 14, 16, 18, 20, 22) and now.minute == 0:
				report = {}
				report["attachments"] = [{'text': "QA/Dev Worklog bot is working!"}]
				logger.info("Sending status")
				response = send(config.webhook_test, payload=report)
				logger.info("Response: {}".format(response))
				time.sleep(60)
			
			time.sleep(30)
		except Exception as ex:
			logger.info("Exception: {}".format(ex))

if __name__ == "__main__":
	monitoring()