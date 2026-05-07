"""GitHub Action entrypoint for Breakwatch."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from breakwatch.classifier import Severity, classify
from breakwatch.diff import diff_specs
from breakwatch.filter import filter_for_consumer
from breakwatch.formatters.markdown import format_check_markdown
from breakwatch.graph import GraphLoadError, load_graph
from breakwatch.loader import SpecLoadError, load_spec


def get_input(name: str, required: bool = True) -> str:
    """Read a GitHub Action input from environment variables.

    GitHub Actions passes inputs as INPUT_<NAME> environment variables,
    with the name uppercased and hyphens replaced by underscores.
    """
    env_name = f"INPUT_{name.upper().replace('-', '_')}"
    value = os.environ.get(env_name, "").strip()
    if required and not value:
        print(f"::error::Missing required input: {name}")
        sys.exit(2)
    return value


def run() -> None:
    """Main entrypoint for the GitHub Action.

    Reads inputs from environment, runs the full pipeline,
    posts a PR comment, and sets the commit status.
    """
    # Read inputs
    config_path = get_input("config")
    producer = get_input("producer")
    old_spec_path = get_input("old-spec")
    new_spec_path = get_input("new-spec")
    fail_on_breaking = get_input("fail-on-breaking", required=False) != "false"
    github_token = get_input("github-token", required=False)

    # GitHub context from environment
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    github_sha = os.environ.get("GITHUB_SHA", "")
    github_event_name = os.environ.get("GITHUB_EVENT_NAME", "")

    # Read PR number from event payload
    pr_number = _get_pr_number()

    # Load graph
    try:
        graph = load_graph(Path(config_path))
    except GraphLoadError as exc:
        print(f"::error::Failed to load config: {exc}")
        sys.exit(2)

    if producer not in graph.producers:
        print(
            f"::error::Unknown producer: {producer}. "
            f"Available: {', '.join(graph.producers.keys())}"
        )
        sys.exit(2)

    # Load specs
    try:
        old_spec = load_spec(Path(old_spec_path))
    except SpecLoadError as exc:
        print(f"::error::Failed to load old spec: {exc}")
        sys.exit(2)

    try:
        new_spec = load_spec(Path(new_spec_path))
    except SpecLoadError as exc:
        print(f"::error::Failed to load new spec: {exc}")
        sys.exit(2)

    # Diff, classify, and filter per consumer
    changes = diff_specs(old_spec, new_spec)
    classified = classify(changes)

    consumers = graph.consumers_of(producer)
    results: dict[str, list] = {}
    for consumer in consumers:
        filtered = filter_for_consumer(classified, consumer, producer)
        results[consumer.name] = filtered

    # Generate markdown report
    markdown = format_check_markdown(producer, results)

    # Determine overall status
    has_breaking = any(
        any(c.severity == Severity.BREAKING for c in changes_list)
        for changes_list in results.values()
    )

    # Post PR comment if we have a token and PR number
    if github_token and pr_number and github_repo:
        try:
            from breakwatch.github import post_pr_comment, set_commit_status

            post_pr_comment(github_token, github_repo, pr_number, markdown)
            print(f"::notice::Posted Breakwatch report to PR #{pr_number}")

            # Set commit status
            if github_sha:
                state = "failure" if has_breaking else "success"
                description = (
                    f"Breaking changes detected for {sum(1 for c in results.values() if any(x.severity == Severity.BREAKING for x in c))} consumer(s)"
                    if has_breaking
                    else "No breaking changes"
                )
                set_commit_status(
                    github_token, github_repo, github_sha, state, description
                )
        except Exception as exc:
            print(f"::warning::Failed to post GitHub comment: {exc}")

    # Write output
    print(markdown)

    # Set GitHub Action outputs
    _set_output("has-breaking", str(has_breaking).lower())
    _set_output("report", markdown)

    # Exit code
    if has_breaking and fail_on_breaking:
        sys.exit(1)


def _get_pr_number() -> int | None:
    """Extract PR number from GitHub event payload."""
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path or not Path(event_path).exists():
        return None

    try:
        with open(event_path) as f:
            event = json.load(f)
        pr = event.get("pull_request") or event.get("issue", {})
        return pr.get("number")
    except (json.JSONDecodeError, KeyError):
        return None


def _set_output(name: str, value: str) -> None:
    """Set a GitHub Action output variable."""
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"{name}={value}\n")


if __name__ == "__main__":
    run()
