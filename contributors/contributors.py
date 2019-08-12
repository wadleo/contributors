# -*- coding: utf-8 -*-

"""
1. Get list of repos desired to be checked for sprinters
2. For each repo:
    A. Get a list of committers
    B. Get a list of those who filed new issues
    C. Get a list of those who submitted unnaccepted pull requests
    D. Combine lists into a Python set
3. Generate a RST (or markdown) list from the data. Each element includes
    A. GitHub username
    B. Personal name if different
    C. Link to user profile on GitHub

"""

from __future__ import absolute_import, print_function

from os import environ

from github3 import GitHub

# from gitlab import Gitlab

from . import utils

gh = GitHub()
token = environ.get('GITHUB_API_SECRET')
if token:
    gh.login(token=token)

# gl_token = environ.get('GITLAB_API_SECRET')
# if gl_token:
#     gl = Gitlab(url='https://gitlab.com', private_token=gl_token)
#     gl.auth()


def get_html_output(contributors):
    column_size = 5

    def format_user_info(user):
        if user.name:
            return template_with_name.format(
                name=user.name,
                link=user.html_url,
                username=user.login)
        else:
            return template_no_name.format(
                link=user.html_url,
                username=user.login)

    # generate html now
    column_template = '    <td align=center><img width=100 src={photo}>'
    column_template += '<br>{name}</td>\n'
    template_with_name = '{name} (<a href={link}>@{username}</a>)'
    template_no_name = '<a href={link}>@{username}</a>'

    output = "<table>\n"
    for row_data in utils.chunks(contributors, column_size):
        output += '  <tr>\n'
        for user in row_data:
            output += column_template.format(
                photo=user.avatar_url,
                name=format_user_info(user))
        output += '  </tr>\n'
    output += '</table>\n'
    return output


def get_markdown_output(contributors):
    output = []
    template_with_name = "* {name} ([@{username}]({link}))"
    template_no_name = "* [@{username}]({link})"

    for user in contributors:
        print('.', end='', flush=True)
        if user.name.strip():
            output.append(template_with_name.format(
                name=user.name,
                username=user.login,
                link=user.html_url))
        else:
            output.append(template_no_name.format(
                username=user.login,
                link=user.html_url))

    return '\n'.join(output) + '\n'


def get_rst_output(contributors):
    links = ""
    output = []
    for user in contributors:
        if user.name:
            output.append("  * {name} (`@{username}`_)".format(
                name=user.name, username=user.login))
        else:
            output.append("  * `@{username}`_".format(username=user.login))

        links += ".. _`@{username}`: {html_url}\n".format(
            username=user.login,
            html_url=user.html_url
        )
    statement = "Generated by https://github.com/pydanny/contributors\n\n"
    return statement + '\n'.join(output) + '\n' + links


def get_output_text(contributors, format):
    mapping = {
        'rst': get_rst_output,
        'md': get_markdown_output,
        'markdown': get_markdown_output,
        'html': get_html_output,
    }
    assert format in mapping.keys(), "Unsuppored format"
    return mapping[format](contributors)


def get_contributors_github(repo_names, since=None, until=None, format='rst'):
    """
    :param repo_names: List of GitHub repos, each named thus:
                        ['audreyr/cookiecutter', 'pydanny/contributors']
    :param since: Only commits after this date will be returned. This is a
                        timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.
    :param until: Only commits before this date will be returned. This is a
                        timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.
    """
    if gh.ratelimit_remaining < 1000:
        proceed = input(
            "Your GitHub rate limit is below 1000. Continue? (y/n)")
        if proceed.lower() != 'y':
            return

    contributors = set([])

    print('Starting aggregating sprinters across projects')
    for repo_name in repo_names.split(','):
        print('\nFetching data for', repo_name)

        # Get the repo object from GitHub
        user_name, repo_name = repo_name.split('/')
        repo = gh.repository(user_name, repo_name)

        # Get commit contributors
        for commit in repo.commits(since=since, until=until):
            print('.', end='', flush=True)
            if commit.author is not None:
                contributors.add(str(commit.author))

        # Get pull-request/ issue creators
        for issue in repo.issues(state='closed', since=since):
            # If the issues are created after until, skip this record
            if until and issue.created_at > until:
                continue
            contributors.add(str(issue.user))

    def fetch_user(username):
        print('.', end='', flush=True)
        return gh.user(username)

    print('\nFetching user info:')
    contributors = map(fetch_user, contributors)
    contributors = sorted(
        contributors,
        key=lambda x: x.name.lower() if x.name else x.login.lower())

    print('\nBuilding output')
    return get_output_text(contributors, format)


# def get_contributors_gitlab(repo_name):
#     project = gl.projects.get(repo_name)
#     commits = project.commits.list()
#     print(type(commits))
