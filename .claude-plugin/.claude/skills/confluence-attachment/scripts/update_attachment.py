#!/usr/bin/env python3
"""
Update/replace an existing attachment on Confluence.

Examples:
    python update_attachment.py att123456 --file new_version.pdf
    python update_attachment.py att123456 --file updated_doc.docx --comment "Fixed typos"
"""

import argparse
from pathlib import Path
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    validate_file_path, print_success, format_attachment, format_json,
    print_info,
)


@handle_errors
def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(
        description='Update/replace an existing attachment on Confluence',
        epilog='''
Examples:
  python update_attachment.py att123456 --file new_version.pdf
  python update_attachment.py att123456 --file updated.docx --comment "Updated content"
  python update_attachment.py att123456 --file report_v2.xlsx --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('attachment_id', help='Attachment ID to update')
    parser.add_argument('--file', '-f', required=True, type=Path, help='New file to upload')
    parser.add_argument('--comment', '-c', help='Version comment or description')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args(argv)

    # Validate inputs
    attachment_id = validate_page_id(args.attachment_id)
    file_path = validate_file_path(args.file, must_exist=True, must_be_file=True)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Get current attachment info
    current_attachment = client.get(
        f"/api/v2/attachments/{attachment_id}",
        operation=f"get attachment {attachment_id}"
    )

    current_version = current_attachment.get('version', {}).get('number', 0)
    print_info(f"Current version: {current_version}")
    print_info(f"Updating with file: {file_path.name}")

    # Prepare additional data
    additional_data = {}
    if args.comment:
        additional_data['comment'] = args.comment

    # Update the attachment
    # For Confluence v2 API, updating is typically done by uploading a new version
    # The endpoint may vary - common patterns:
    # 1. PUT /api/v2/attachments/{id}/data
    # 2. POST to same page with same filename (creates new version)

    # Try the data endpoint first
    endpoint = f"/api/v2/attachments/{attachment_id}/data"

    try:
        result = client.upload_file(
            endpoint,
            file_path,
            additional_data=additional_data if additional_data else None,
            operation=f"update attachment {attachment_id}"
        )
    except Exception as e:
        # If that fails, fall back to uploading to the page with same filename
        print_info("Trying alternate update method...")
        page_id = current_attachment.get('pageId')
        if not page_id:
            raise ValidationError(f"Could not determine page ID for attachment {attachment_id}")

        endpoint = f"/api/v2/pages/{page_id}/attachments"
        result = client.upload_file(
            endpoint,
            file_path,
            additional_data=additional_data if additional_data else None,
            operation=f"update attachment {attachment_id} on page {page_id}"
        )

    # Extract attachment from response
    attachments = result.get('results', [])
    if not attachments:
        # Sometimes update returns the attachment directly
        attachment = result
    else:
        attachment = attachments[0]

    # Output
    if args.output == 'json':
        print(format_json(attachment))
    else:
        print(format_attachment(attachment))

    new_version = attachment.get('version', {}).get('number', current_version + 1)
    print_success(f"Updated attachment {attachment_id} to version {new_version}")

if __name__ == '__main__':
    main()
