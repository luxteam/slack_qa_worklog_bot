import os
import time
import datetime
import operator

from webhookHandler import send
import config
import jiraHandler


def createReport(persons):

	jira_report = {}

	for person in persons:
		# get day of week, 0 - monday.
		weekday = datetime.datetime.today().weekday()
		if weekday: # not monday
			# get 2 days ago date, not 1 day ago, because timezone of jira server is -7 from UTC, so we get more large border (+1 day)
			two_days_ago = (datetime.datetime.today() - datetime.timedelta(days=2)).strftime("%Y/%m/%d")
			# get current date, not yesterday, because we take more large border
			today = datetime.datetime.today().strftime("%Y/%m/%d")
			# make jql for jira filter
			jql = "worklogDate >= \'{}\' and worklogDate <= \'{}\' and worklogAuthor = \'{}\'".format(two_days_ago, today, person)
			# get workdate (yesterday)
			work_date = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y/%m/%d")
			# get jira worklog for current person
			jira_report[person] = jiraHandler.getDayWorkLog(jql, work_date, work_date, person)
		else: # monday, we take holidays to log
			# get 4 days ago date, not 3 day ago, because timezone of jira server is -7 from UTC and we add holidays to log, so we get more large border (+4 day)
			four_days_ago = (datetime.datetime.today() - datetime.timedelta(days=4)).strftime("%Y/%m/%d")
			# get current date, not yesterday, because we take more large border
			today = datetime.datetime.today().strftime("%Y/%m/%d")
			# make jql for jira filter
			jql = "worklogDate >= \'{}\' and worklogDate <= \'{}\' and worklogAuthor = \'{}\'".format(four_days_ago, today, person)
			# get workdate (friday) and yesterday (sunday)
			work_date = (datetime.datetime.today() - datetime.timedelta(days=3)).strftime("%Y/%m/%d")
			yesterday = (datetime.datetime.today() - datetime.timedelta(days=1)).strftime("%Y/%m/%d")
			# get jira worklog for current person
			jira_report[person] = jiraHandler.getDayWorkLog(jql, work_date, yesterday, person)

	slack_report = []

	# generate slack report message
	for person in persons:
		jira_report[person] = sorted(jira_report[person].items(), key=operator.itemgetter(0))
		slack_report.append(createPersonJson(person, jira_report[person]))

	# create slack message
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

	report = {}
	report["attachments"] = [{'text': "Worklog bot was started!"}]
	send(config.webhook_test, payload=report)

	while True:
		try:
			weekday = datetime.datetime.today().weekday()
			now = datetime.datetime.now()
			if weekday in range(0, 4) and now.hour == 6 and now.minute == 30:
				send(config.webhook_qa, payload=createReport(config.qa))
				send(config.webhook_dev, payload=createReport(config.dev))
				time.sleep(60)
			
			time.sleep(30)
		except Exception as ex:
			print(ex)

if __name__ == "__main__":
	monitoring()
