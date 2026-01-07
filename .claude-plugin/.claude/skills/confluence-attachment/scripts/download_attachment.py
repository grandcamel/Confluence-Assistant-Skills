#!/usr/bin/env python3
"""
Download an attachment from Confluence.

Examples:
    python download_attachment.py att123456 --output ./downloads/
    python download_attachment.py att123456 --output myfile.pdf
    python download_attachment.py 123456 --all --output ./downloads/
"""

import argparse
from pathlib import Path

from confluence_assistant_skills_lib import (
    ValidationError,
    get_confluence_client,
    handle_errors,
    print_info,
    print_success,
    validate_page_id,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description="Download attachment(s) from Confluence",
        epilog="""
Examples:
  # Download single attachment by ID
  python download_attachment.py att123456 --output ./downloads/

  # Download with specific filename
  python download_attachment.py att123456 --output myfile.pdf

  # Download all attachments from a page
  python download_attachment.py 123456 --all --output ./downloads/
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("id", help="Attachment ID or Page ID (with --all flag)")
    parser.add_argument(
        "--output", "-o", required=True, type=Path, help="Output file or directory"
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Download all attachments from page"
    )
    parser.add_argument("--profile", help="Confluence profile to use")
    args = parser.parse_args(argv)

    # Validate inputs
    item_id = validate_page_id(args.id)  # Works for both page and attachment IDs

    # Get client
    client = get_confluence_client(profile=args.profile)

    if args.all:
        # Download all attachments from page
        page_id = item_id

        # Get all attachments on the page
        attachments = list(
            client.paginate(
                f"/api/v2/pages/{page_id}/attachments",
                operation=f"list attachments on page {page_id}",
            )
        )

        if not attachments:
            print("No attachments found on page.")
            return

        # Ensure output is a directory
        output_dir = args.output
        if not output_dir.exists():
            output_dir.mkdir(parents=True)
        elif not output_dir.is_dir():
            raise ValidationError(
                f"Output path must be a directory when using --all: {output_dir}"
            )

        # Download each attachment
        downloaded = []
        for att in attachments:
            filename = att.get("title", f"attachment_{att['id']}")
            output_file = output_dir / filename

            # Get download URL
            download_link = att.get(
                "downloadLink", att.get("_links", {}).get("download")
            )
            if not download_link:
                print_info(f"Skipping {filename}: no download link")
                continue

            print_info(f"Downloading {filename}...")
            client.download_file(
                download_link, output_file, operation=f"download attachment {att['id']}"
            )
            downloaded.append(filename)

        print_success(f"Downloaded {len(downloaded)} attachment(s) to {output_dir}")

    else:
        # Download single attachment
        attachment_id = item_id

        # Get attachment metadata
        attachment = client.get(
            f"/api/v2/attachments/{attachment_id}",
            operation=f"get attachment {attachment_id}",
        )

        # Determine output path
        if args.output.is_dir() or str(args.output).endswith("/"):
            # Output is directory, use attachment filename
            output_dir = args.output
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = attachment.get("title", f"attachment_{attachment_id}")
            output_file = output_dir / filename
        else:
            # Output is specific file
            output_file = args.output
            output_file.parent.mkdir(parents=True, exist_ok=True)

        # Get download URL
        download_link = attachment.get(
            "downloadLink", attachment.get("_links", {}).get("download")
        )
        if not download_link:
            raise ValidationError(
                f"No download link found for attachment {attachment_id}"
            )

        # Download the file
        print_info(f"Downloading {attachment.get('title', 'attachment')}...")
        result = client.download_file(
            download_link, output_file, operation=f"download attachment {attachment_id}"
        )

        print_success(f"Downloaded to {result}")


if __name__ == "__main__":
    main()
