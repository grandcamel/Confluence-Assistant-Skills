---
name: confluence-attachment
description: Manage file attachments - upload, download, list, and delete attachments
triggers:
  - attach
  - attachment
  - upload file
  - download file
  - upload attachment
  - download attachment
---

# Confluence Attachment Skill

Manage file attachments on Confluence pages.

## Available Scripts

### upload_attachment.py
Upload a file to a page.

**Usage:**
```bash
confluence attachment upload PAGE_ID FILE_PATH
confluence attachment upload 12345 report.pdf
confluence attachment upload 12345 image.png --comment "Screenshot"
```

### download_attachment.py
Download an attachment.

**Usage:**
```bash
confluence attachment download ATTACHMENT_ID --output ./downloads/
confluence attachment download att123456 --output myfile.pdf
confluence attachment download 12345 --all --output ./downloads/  # Download all from page
```

### list_attachments.py
List attachments on a page.

**Usage:**
```bash
confluence attachment list 12345
confluence attachment list 12345 --output json
confluence attachment list 12345 --output table
confluence attachment list 12345 --media-type application/pdf
```

### delete_attachment.py
Remove an attachment.

**Usage:**
```bash
confluence attachment delete ATTACHMENT_ID
confluence attachment delete ATTACHMENT_ID --force
```

### update_attachment.py
Replace an attachment file.

**Usage:**
```bash
confluence attachment update ATTACHMENT_ID FILE_PATH
confluence attachment update att123456 new_version.pdf
confluence attachment update att123456 updated.docx --comment "Updated content"
```
