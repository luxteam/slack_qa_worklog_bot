import os
import time
import datetime
import operator

from webhookHandler import send
import config
import jiraHandler


def createReport():

	jira_report = {}

	persons = config.persons
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


def createPersonJson(person, data):
	report = {}
	report["title"] = person
	tickets = []
	total_time = 0
	if data:
		for d in data:
			if d[1]['parent_key'] and d[1]['comment']:
				message = "Parent task: [{}] {}\nTime: {}\nLogged time: {}\nComment: {}".format(d[1]['parent_key'], d[1]['parent_summary'], d[0], d[1]['timeSpent'], d[1]['comment'])
			elif d[1]['parent_key']:
				message = "Parent task: [{}] {}\nTime: {}\nLogged time: {}".format(d[1]['parent_key'], d[1]['parent_summary'], d[0], d[1]['timeSpent'])
			elif d[1]['comment']:
				message = "Time: {}\nLogged time: {}\nComment: {}".format(d[0], d[1]['timeSpent'], d[1]['comment'])
			else:
				message = "Time: {}\nLogged time: {}".format(d[0], d[1]['timeSpent'])
			tickets.append({"title": "[{}] {}".format(d[1]['key'], d[1]['summary']) , "value": message, "short": False})
			total_time += d[1]['timeSpentSeconds']
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

	send(payload=createReport())
	while True:
		try:
			weekday = datetime.datetime.today().weekday()
			now = datetime.datetime.now()
			if weekday in range(0, 4) and now.hour == 9 and now.minute == 30:
				send(payload=createReport())
				time.sleep(60)
			
			time.sleep(30)
		except Exception as ex:
			print(ex)

if __name__ == "__main__":
	monitoring()
