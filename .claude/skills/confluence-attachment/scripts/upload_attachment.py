#!/usr/bin/env python3
"""
Upload a file attachment to a Confluence page.

Examples:
    python upload_attachment.py 123456 --file report.pdf
    python upload_attachment.py 123456 --file image.png --comment "Screenshot of bug"
    python upload_attachment.py 123456 --file document.docx --profile production
"""

import sys
import argparse
from confluence_assistant_skills_lib import (
    get_confluence_client, handle_errors, ValidationError, validate_page_id,
    validate_file_path, print_success, format_attachment, format_json,
)


@handle_errors
def main():
    parser = argparse.ArgumentParser(
        description='Upload a file attachment to a Confluence page',
        epilog='''
Examples:
  python upload_attachment.py 123456 --file report.pdf
  python upload_attachment.py 123456 --file image.png --comment "Screenshot"
  python upload_attachment.py 123456 --file doc.docx --profile production
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('page_id', help='Page ID to attach file to')
    parser.add_argument('--file', '-f', required=True, type=Path, help='File to upload')
    parser.add_argument('--comment', '-c', help='Comment or description for the attachment')
    parser.add_argument('--profile', help='Confluence profile to use')
    parser.add_argument('--output', '-o', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    args = parser.parse_args()

    # Validate inputs
    page_id = validate_page_id(args.page_id)
    file_path = validate_file_path(args.file, must_exist=True, must_be_file=True)

    # Get client
    client = get_confluence_client(profile=args.profile)

    # Prepare additional data
    additional_data = {}
    if args.comment:
        additional_data['comment'] = args.comment

    # Upload the file
    endpoint = f"/api/v2/pages/{page_id}/attachments"
    result = client.upload_file(
        endpoint,
        file_path,
        additional_data=additional_data if additional_data else None,
        operation=f"upload attachment to page {page_id}"
    )

    # Extract attachment from response
    # v2 API returns {"results": [attachment]}
    attachments = result.get('results', [])
    if not attachments:
        raise ValidationError("No attachment returned from API")

    attachment = attachments[0]

    # Output
    if args.output == 'json':
        print(format_json(attachment))
    else:
        print(format_attachment(attachment))

    print_success(f"Uploaded '{file_path.name}' to page {page_id} (Attachment ID: {attachment['id']})")

if __name__ == '__main__':
    main()
