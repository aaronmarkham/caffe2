"""
This script will generate markdown for a Github project's release notes.
It will access the Github API and query Issues with specific params.
It is setup to get these labels and generate a table for each:
    enhancement
    bug
    build
    documentation
It will also tally up contributors and generate ranked lists for each label.

Configuration:
    repo - specify the project repo (owner/repo)
    since - specify how far you want to go back (when was the last release?)
    limit - how long you want the output for the summary column to be
    list - pull the list of labels from the repo
    labels - space delimited list of which labels to report on
    all - use all of the labels in the repo
    message - a special (thank you) message for the contributors

TODO:
* add custom messages to each section
* use a config file + templating
* use authentication to prevent rate limited by Github API
* replace rank number with icons; have different layout options
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
import argparse
from collections import Counter
import datetime
import dateutil.relativedelta
import json
import requests
import sys

# Deals with some encoding errors that might come up: unicode vs ascii
reload(sys)
sys.setdefaultencoding('utf8')


def getLabels(url):
    # Load and prep the json data from the API
    data = requests.get(url=url)
    binary = data.content
    output = json.loads(binary)
    labels = []
    if output['message'] == "Not Found":
        print("That repo and/or label was not found.")
    else:
        for result in output:
            labels.append(result['name'].encode('utf-8'))
    return labels

def generateList(contributors, counter, label):
    """
    Ranks the contributors and prints the list
    """
    label = label.capitalize()
    # No one wants to be listed as Bug Contributor
    if label == "Bug":
        label = "Bug Fix"
    print("\n### {} Contributors\n".format(label))
    # Sort the counter
    ranked = counter.most_common()
    for user, _rank in ranked:
        # List with counts in long form
        # print("[{}]({}): {}".format(user, contributors[user], counter[user]))
        # List with no counts in short form
        print("[{}]({})".format(user, contributors[user]), end=' ')
    print("\n")


def generateTable(url, params, limit, c):
    """
    Creates a markdown table from Github issues
    """

    def bodyBreaker(body, width):
        parts = body.split()
        # Break the body into parts but only keep the parts
        body = ""
        for word in parts:
            if len(word) > width:
                # If word is longer than 64 chars then trim it
                word = (word[:width] + '..')
            # Resurrection of the body maybe missing a little bit
            body += word + ' '
        return body

    # Load and prep the json data from the API
    data = requests.get(url=url, params=params)
    binary = data.content
    output = json.loads(binary)
    # Start the counter for the number of issues loaded
    total = 0
    # Create a list of user, user_url entries
    contributors = {}

    label = params.get("labels").capitalize()
    if label == "Bug":
        label = "Bug Fix"
    print("\n## {} Updates".format(label))
    intro = "\n| Title | Summary | Contributor |\n|---|---|---|"
    print(intro)

    for result in output:
        # Filter PRs optional -->    if 'pull_request' in result:
        # Non-UTF-8 characters sometimes appear and cause issues
        # Line breaks will break the markdown
        title = result['title'].encode('utf-8').replace('\n', ' ') \
            .replace('\r', '')
        title = bodyBreaker(title, 25)
        url = result['html_url']
        # Trim the body to the max limit and remove bad stuff
        # Backticks with long code blocks mess up formatting
        body = result['body'][0:limit].encode('utf-8').replace('\n', ' ') \
            .replace('\r', '').replace('`', '')
        # If the body is too long add ... to show there is more
        if (len(result['body']) > limit):
            body += '...'
        # Sometimes there are long words that force the column widths too wide
        body = bodyBreaker(body, 50)
        # Naughty developers that don't add any details get an n/a
        if len(body) == 0:
            body = 'n/a'
        user = result['user']['login'].encode('utf-8')
        user_url = result['user']['html_url']
        # Add user to contributors list
        contributors[user] = user_url
        c[user] += 1
        print("|[{}]({})|{}|[{}]({})|".format(title, url, body, user, user_url))
        total += 1

    # Check output totals
    print("Total of {} out of {}\n".format(total, len(output)))
    return contributors, c


def main():
    print("Pulling from {} and generating reports on these labels: {}".format(repo, labels))
    for label in labels:
        params = dict(
            labels=label,
            state='closed',
            since=since
        )
        this_counter = Counter()
        contributors, this_counter = generateTable(url_issues, params, limit, this_counter)
        generateList(contributors, this_counter, label)


if __name__ == "__main__":
    now = datetime.datetime.now()
    since_default = now - dateutil.relativedelta.relativedelta(months=1)
    parser = argparse.ArgumentParser(
        description='Create release notes from the Github API')
    parser.add_argument('--repo', action='store', dest='repo',
                default='caffe2/caffe2',
                help='The Github API URL to your project Issues, default=\
                    (caffe2/caffe2)')
    parser.add_argument('--since', action='store', dest='since',
                default=since_default,
                help='Date to report since (YYYY-MM-DD), default=a month ago')
    parser.add_argument('--limit', action='store', dest='limit', default=180,
                help='Length of summary column, default=180')
    parser.add_argument('--list', action='store_true', dest='list', default=False,
                help='Fetches the list of labels in the repo, default=False')
    parser.add_argument('--labels', action='store', dest='labels', nargs='+',
                default=['bug'], help='List of labels to report')
    parser.add_argument('--all', action='store', dest='all', default=False,
                help='Report on all labels in the repo, default=False')
    parser.add_argument('--message', action='store',
                dest='message',
                default='A big thank you to the contributors for this release!',
                help='A nice message for the contributors, \
                    default=A big thank you to the contributors \
                    for this release!')
    args = parser.parse_args()
    repo = args.repo
    since = args.since
    limit = args.limit
    labels_check = args.list
    labels = args.labels
    labels_all = args.all
    contributors_message = args.message
    # Reformat repo:  https://api.github.com/repos/caffe2/caffe2/issues
    url_issues = "https://api.github.com/repos/{}/issues".format(repo)
    url_labels = "https://api.github.com/repos/{}/labels".format(repo)
    # User asked for a list of labels or all, so get 'em
    if labels_check or labels_all:
        # Hit the API and fetch all label names from the repo
        labels = getLabels(url_labels)
    if labels_check:
        print("As requested, here are the repo's labels: {}".format(labels))
        print("Don't use --list next time if you want your issues outputs.")
    else:
        main()
