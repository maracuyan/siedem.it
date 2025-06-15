import os
import sys
from github import Github

# Name of the current workflow, to be excluded from checks
WORKFLOW_NAME = "Auto Create and Merge PR"

def automerge():
    print("Automerge script started.")

    github_token = os.environ.get("GITHUB_TOKEN")
    pr_number_str = os.environ.get("PR_NUMBER")
    repo_name = os.environ.get("GITHUB_REPOSITORY")

    if not github_token:
        print("Error: GITHUB_TOKEN not found in environment variables.")
        sys.exit(1)
    if not pr_number_str:
        print("Error: PR_NUMBER not found in environment variables.")
        sys.exit(1)
    if not repo_name:
        print("Error: GITHUB_REPOSITORY not found in environment variables.")
        sys.exit(1)

    try:
        pr_number = int(pr_number_str)
    except ValueError:
        print(f"Error: Invalid PR_NUMBER: {pr_number_str}. Must be an integer.")
        sys.exit(1)

    g = Github(github_token)
    try:
        repo = g.get_repo(repo_name)
        # It's good practice to re-fetch the PR to get the most up-to-date state
        pull_request = repo.get_pull(pr_number)
    except Exception as e:
        print(f"Error getting repository or pull request: {e}")
        sys.exit(1)

    print(f"Checking PR #{pull_request.number}: {pull_request.title}")
    print(f"PR URL: {pull_request.html_url}")

    # Check if the PR is already merged or closed
    if pull_request.merged:
        print(f"PR #{pull_request.number} is already merged.")
        sys.exit(0)
    if pull_request.closed_at:
        print(f"PR #{pull_request.number} is closed and cannot be merged.")
        sys.exit(0)
    if pull_request.draft:
        print(f"PR #{pull_request.number} is a draft and cannot be merged.")
        sys.exit(0)

    # First, verify all explicit checks (check suites and statuses)
    commit_sha = pull_request.head.sha
    print(f"Head commit SHA: {commit_sha}")

    all_explicit_checks_passed = True

    # Verify check suites
    try:
        check_suites = repo.get_commit(commit_sha).get_check_suites()
        print(f"Found {check_suites.totalCount} check suites.")
        for suite in check_suites:
            # Exclude the current automerge workflow itself from the checks
            if suite.app.name == WORKFLOW_NAME or suite.app.id == g.get_app().id: # More robust check for current workflow
                print(f"Skipping check suite from workflow: {suite.app.name} (Status: {suite.status}, Conclusion: {suite.conclusion})")
                continue

            print(f"Check Suite: {suite.app.name}, Status: {suite.status}, Conclusion: {suite.conclusion}")
            if suite.conclusion != 'success':
                print(f"Check suite '{suite.app.name}' did not succeed. Conclusion: {suite.conclusion}.")
                all_explicit_checks_passed = False
    except Exception as e:
        print(f"Error fetching check suites: {e}")
        all_explicit_checks_passed = False # Treat errors in fetching as checks not passed

    # Verify statuses (legacy API, but some tools still use it)
    try:
        statuses = repo.get_commit(commit_sha).get_statuses()
        print(f"Found {statuses.totalCount} statuses.")
        for status in statuses:
            # Exclude the current automerge workflow itself from the statuses
            if status.context == WORKFLOW_NAME or (status.creator and status.creator.login == "github-actions"):
                print(f"Skipping status: {status.context} (State: {status.state})")
                continue

            print(f"Status Context: {status.context}, State: {status.state}")
            if status.state != 'success':
                print(f"Status '{status.context}' did not succeed. State: {status.state}.")
                all_explicit_checks_passed = False
    except Exception as e:
        print(f"Error fetching statuses: {e}")
        all_explicit_checks_passed = False # Treat errors in fetching as checks not passed


    if not all_explicit_checks_passed:
        print(f"PR #{pull_request.number} (commit {commit_sha}) will not be merged because not all explicit checks passed.")
        sys.exit(0) # Exit gracefully, this is not an error in the script itself


    # Now, check GitHub's own mergeability status as a final safeguard
    # Refresh the PR data to ensure mergeability status is current
    pull_request.update()

    print(f"PR Mergeable: {pull_request.mergeable}")
    print(f"PR Mergeable State: {pull_request.mergeable_state}")

    # GitHub's mergeable_state can be:
    # 'clean' -> merging is possible
    # 'dirty' -> merge conflicts
    # 'unknown' -> still being computed
    # 'blocked' -> blocked by failing checks or other restrictions
    # 'unstable' -> non-critical checks failed, but mergeable
    # 'draft' -> PR is a draft (already checked above)
    # 'behind' -> head branch is behind the base branch

    if not pull_request.mergeable:
        print(f"PR #{pull_request.number} is not mergeable according to GitHub API.")
        print(f"Mergeable: {pull_request.mergeable}, Mergeable State: '{pull_request.mergeable_state}'.")
        sys.exit(0) # Not an error for the script, but PR cannot be merged.

    if pull_request.mergeable_state in ['dirty', 'blocked']:
        print(f"PR #{pull_request.number} is in a non-mergeable state: '{pull_request.mergeable_state}'.")
        sys.exit(0)

    if pull_request.mergeable_state == 'unknown':
        print(f"PR #{pull_request.number} mergeable state is 'unknown'. GitHub is still computing. Exiting.")
        sys.exit(0) # Give it time, or check GitHub UI.

    # If we reach here, all explicit checks passed and the PR is considered mergeable by GitHub's API
    print(f"PR #{pull_request.number} (commit {pull_request.head.sha}) is deemed mergeable by GitHub and all checks passed.")
    try:
        print(f"Attempting to merge PR #{pull_request.number}...")
        # Using a descriptive commit title and message
        commit_title = f"{pull_request.title} (#{pull_request.number})"
        commit_message = f"Auto-merged by Auto Merge action.\n\nOriginal PR message:\n{pull_request.body}"

        pull_request.merge(merge_method="squash", commit_title=commit_title, commit_message=commit_message)
        print(f"Successfully merged PR #{pull_request.number}.")

        # Attempt to delete the branch
        try:
            branch_name = pull_request.head.ref
            print(f"Attempting to delete branch: {branch_name}...")
            git_ref = repo.get_git_ref(f"heads/{branch_name}")
            git_ref.delete()
            print(f"Successfully deleted branch: {branch_name}.")
        except Exception as e:
            print(f"Error deleting branch {branch_name}: {e}")
            # Continue even if branch deletion fails, as merge was successful.

    except Exception as e:
        print(f"Error merging PR #{pull_request.number}: {e}")
        if hasattr(e, 'data'):
            print(f"GitHub API Error Data: {e.data}")
        sys.exit(1)


if __name__ == "__main__":
    automerge()