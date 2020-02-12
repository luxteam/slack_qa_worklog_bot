import time
import config
import requests
import datetime
from jira import JIRA


# create jira client connection
def createJiraClient():
	jira_options = {'server': config.amd_jira_host}
	return JIRA(options=jira_options, basic_auth=(config.amd_jira_username, config.amd_jira_token))


def getIssuesListFronJQL(jql):
	jira_client = createJiraClient()
	issue_dict = jira_client.search_issues(jql, maxResults=100, json_result=True)

	issues_keys = []
	for i in issue_dict['issues']:
		issues_keys.append(i['key'])

	startAt = 100
	while len(issue_dict['issues']) == 100:
		issue_dict = jira_client.search_issues(jql, startAt=startAt, maxResults=100, json_result=True)
		for i in issue_dict['issues']:
			issues_keys.append(i['key'])
		startAt += 100

	jira_client.close()
	return issues_keys


# get ticket json, api doesn't return worklog, so we use get request to jira server
def getTicketWorklog(ticket):
	response = requests.get("{}/rest/api/2/issue/{}/worklog".format(config.amd_jira_host, ticket), auth=(config.amd_jira_username, config.amd_jira_token))
	worklogs = response.json()['worklogs']
	return worklogs


def getIssueInfo(ticket):
	response = requests.get("{}/rest/api/2/issue/{}".format(config.amd_jira_host, ticket), auth=(config.amd_jira_username, config.amd_jira_token))
	issueInfo = response.json()
	return issueInfo


# return daily worklog using jql, date and person name.
def getDayWorkLog(jql, friday_or_yesterday_date, sunday_or_yesterday_date, person_id, persons):
	issues_list = getIssuesListFronJQL(jql)
	day_worklog = {}
	for issue in issues_list:
		issueInfo = getIssueInfo(issue)
		worklogs = getTicketWorklog(issue)
		for worklog in worklogs:
			worklog_date = (datetime.datetime.strptime(worklog['started'][:19], '%Y-%m-%dT%H:%M:%S') + datetime.timedelta(hours=11)).strftime("%Y/%m/%d")
			if worklog_date >= friday_or_yesterday_date and worklog_date <= sunday_or_yesterday_date and (worklog['author']['accountId'] == person_id or worklog['author']['displayName'] == persons[person_id]):
				worklog_time = (datetime.datetime.strptime(worklog['started'][:19], '%Y-%m-%dT%H:%M:%S') + datetime.timedelta(hours=11)).strftime("%H:%M:%S")
				
				comment = ''
				if 'comment' in worklog.keys():
					comment = worklog['comment']

				parent_key, parent_summary = ('', '')
				if 'parent' in issueInfo['fields'].keys():
					parent_key = issueInfo['fields']['parent']['key']
					parent_summary = issueInfo['fields']['parent']['fields']['summary']

				worklog_dict = {'key': issueInfo['key'], 'summary': issueInfo['fields']['summary'], 'parent_key': parent_key, 'parent_summary': parent_summary, \
						'timeSpent': worklog['timeSpent'], 'timeSpentSeconds': worklog['timeSpentSeconds'], 'comment': comment}

				if worklog_time in day_worklog.keys():
					day_worklog[worklog_time].append(worklog_dict)
				else:
					day_worklog[worklog_time] = [worklog_dict]
	return day_worklog




