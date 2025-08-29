import os
import re
import sys
from github import Github

from atlassian import Jira
import requests
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables from .env.local file
load_dotenv('.env.local')


def query_jira_issues(jql_query: str, 
                     url: str = os.environ.get('JIRA_URL'),
                     username: str = os.environ.get('JIRA_USERNAME'),
                     password: str = os.environ.get('JIRA_PASSWORD'),
                     max_results: int = 1000,
                     verbose: bool = False) -> List[Dict[str, Any]]:
    
    try:
        session = requests.Session()
        jira = Jira(
            url=url,
            username=username,
            password=password,
            cloud=True,
            session=session
        )

        issues_data = jira.jql(jql_query, limit=max_results)
        if not issues_data or 'issues' not in issues_data:
            return []

        issues = issues_data['issues']
        if not issues:
            return []

        work_items = []
        for issue in issues:
            fields = issue['fields']
            work_item = {
                'key': issue['key'],
                'id': issue['id'],
                'issue_type': fields.get('issuetype', {}).get('name', '') if fields.get('issuetype') else '',
                'status': fields.get('status', {}).get('name', '') if fields.get('status') else '',
            }
            work_items.append(work_item)
        
        return work_items
        
    except Exception as e:
        error_msg = f"Error executing Jira query: {str(e)}"
        raise Exception(error_msg)

def is_standard_issue(work_item_key: str) -> bool:
    work_item = query_jira_issues(f'issueKey = "{work_item_key}"')
    if not work_item:
        return False
    issue_type = work_item[0].get('issue_type', '').lower()
    return issue_type not in ['sub-task', 'epic']


def is_valid_pr_title(title, pattern):
    valid = re.match(pattern, title) is not None
    if valid:
        issue_key = re.search(r"[A-Z]+-\d+", title).group(0)
        valid = is_standard_issue(issue_key)
        if valid:
            return (True, "Title is valid and issue exists in Jira.")
        else:
            return (False, f"Issue key {issue_key} is not a standard issue type or does not exists in JIRA.")
    else:
        return (False, "Title does not match the required pattern.")
    

def validate_required_env_vars(required_vars):
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        print(f'::error::Missing required environment variables: {", ".join(missing_vars)}')
        sys.exit(1)

def main():

    validate_required_env_vars(['TITLE', 'INPUT_JIRA_URL', 'INPUT_JIRA_USERNAME', 'INPUT_JIRA_PASSWORD'])

    pattern = os.environ.get('PATTERN') or r'^(feat|fix|docs|style|refactor|perf|test|chore)\([A-Z]+-\d+\): .+'
    title = os.environ.get('TITLE')
    jira_url = os.environ.get('INPUT_JIRA_URL')
    jira_username = os.environ.get('INPUT_JIRA_USERNAME')
    jira_password = os.environ.get('INPUT_JIRA_PASSWORD')

    (result,error) = is_valid_pr_title(title, pattern)
    if result:
        print(f'::notice::PR title "{title}" is valid.')
        print('::set-output name=valid::true')
        sys.exit(0)
    else:
        print(f'::PR title {title} is not valid - error::{error}')
        print('::set-output name=valid::false')
        sys.exit(1)

if __name__ == '__main__':
    main()
