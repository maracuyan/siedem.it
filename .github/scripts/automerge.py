import os
import sys
from github import Github

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

    # The 'Wait For Status Checks' action in the workflow should ensure checks have passed.
    # This is a final safeguard using GitHub's own mergeability status.
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
    # 'draft' -> PR is a draft
    # 'behind' -> head branch is behind the base branch
    # We primarily care that it's not 'dirty', 'blocked', or 'draft' (though draft should be caught by workflow if-condition)
    # 'clean' is ideal. 'unstable' might be acceptable. 'behind' can sometimes be merged if no conflicts.

    if pull_request.merged:
        print(f"PR #{pull_request.number} is already merged.")
        sys.exit(0)

    if not pull_request.mergeable or pull_request.mergeable_state in ['dirty', 'blocked']:
        print(f"PR #{pull_request.number} is not mergeable or in a non-mergeable state.")
        print(f"Mergeable: {pull_request.mergeable}, Mergeable State: '{pull_request.mergeable_state}'.")
        # Potentially list failing checks if state is 'blocked' and info is available,
        # but the workflow's "Wait For Status Checks" should have already handled this.
        sys.exit(0) # Not an error for the script, but PR cannot be merged.

    if pull_request.mergeable_state == 'unknown':
        print(f"PR #{pull_request.number} mergeable state is 'unknown'. Retrying might be needed or GitHub is still computing. Exiting.")
        sys.exit(0) # Give it time, or check GitHub UI.

    # If we reach here, the PR is considered mergeable by GitHub's API
    print(f"PR #{pull_request.number} (commit {pull_request.head.sha}) is deemed mergeable by GitHub.")
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
