import os
import sys
from github import Github

# Name of the current workflow, to be excluded from checks
WORKFLOW_NAME = "Auto Merge"

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
        pull_request = repo.get_pull(pr_number)
    except Exception as e:
        print(f"Error getting repository or pull request: {e}")
        sys.exit(1)

    print(f"Checking PR #{pull_request.number}: {pull_request.title}")

    commit_sha = pull_request.head.sha
    print(f"Head commit SHA: {commit_sha}")

    all_checks_passed = True

    # Verify check suites
    try:
        check_suites = repo.get_commit(commit_sha).get_check_suites()
        print(f"Found {check_suites.totalCount} check suites.")
        for suite in check_suites:
            if suite.app.name == WORKFLOW_NAME:
                print(f"Skipping check suite from workflow: {suite.app.name} (Status: {suite.status}, Conclusion: {suite.conclusion})")
                continue

            print(f"Check Suite: {suite.app.name}, Status: {suite.status}, Conclusion: {suite.conclusion}")
            if suite.conclusion != 'success':
                print(f"Check suite '{suite.app.name}' did not succeed. Conclusion: {suite.conclusion}.")
                all_checks_passed = False
                # No need to break, let's list all failing checks
    except Exception as e:
        print(f"Error fetching check suites: {e}")
        all_checks_passed = False # Treat errors in fetching as checks not passed

    # Verify statuses
    try:
        statuses = repo.get_commit(commit_sha).get_statuses()
        print(f"Found {statuses.totalCount} statuses.")
        for status in statuses:
            if status.context == WORKFLOW_NAME or (status.creator and status.creator.login == "github-actions"): # More robust check for actions
                # This part might need refinement if WORKFLOW_NAME is not exactly the context.
                # Often, the context for actions is the job name, or workflow name / job name
                # For now, we assume WORKFLOW_NAME or a generic github-actions creator can be skipped
                # A more precise way would be to identify the exact check run ID of this workflow if possible.
                print(f"Skipping status: {status.context} (State: {status.state})")
                continue

            print(f"Status Context: {status.context}, State: {status.state}")
            if status.state != 'success':
                print(f"Status '{status.context}' did not succeed. State: {status.state}.")
                all_checks_passed = False
                # No need to break, let's list all failing statuses
    except Exception as e:
        print(f"Error fetching statuses: {e}")
        all_checks_passed = False # Treat errors in fetching as checks not passed


    if all_checks_passed:
        print(f"All checks for PR #{pull_request.number} (commit {commit_sha}) have passed.")
        try:
            # Before merging, ensure the PR is still mergeable
            # Re-fetch the PR to get its latest state
            pull_request = repo.get_pull(pr_number)
            if pull_request.mergeable:
                print(f"Attempting to merge PR #{pull_request.number}...")
                pull_request.merge(merge_method="squash", commit_title=f"{pull_request.title} (#{pull_request.number})", commit_message=f"Auto-merged by {WORKFLOW_NAME}")
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
                    # For now, just print the error and continue (as the merge was successful)

            else:
                print(f"PR #{pull_request.number} is not mergeable. Mergeable state: {pull_request.mergeable_state}. Mergeability reason: {pull_request.mergeable_state if hasattr(pull_request, 'mergeable_state') else 'N/A'}")
                # Additional details that might be useful
                if pull_request.merged:
                     print(f"PR #{pull_request.number} is already merged.")
                elif pull_request.closed_at:
                     print(f"PR #{pull_request.number} is closed.")

        except Exception as e:
            print(f"Error merging PR #{pull_request.number}: {e}")
            # It might be useful to see more details from the exception if it's a GithubException
            if hasattr(e, 'data'):
                print(f"GitHub API Error Data: {e.data}")
            sys.exit(1)
    else:
        print(f"PR #{pull_request.number} (commit {commit_sha}) will not be merged because not all checks passed.")
        sys.exit(0) # Exit gracefully, this is not an error in the script itself

if __name__ == "__main__":
    automerge()
