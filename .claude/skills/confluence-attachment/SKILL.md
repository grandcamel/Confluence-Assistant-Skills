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
python upload_attachment.py 12345 --file report.pdf
python upload_attachment.py 12345 --file image.png --comment "Screenshot"
```

### download_attachment.py
Download an attachment.

**Usage:**
```bash
python download_attachment.py ATTACHMENT_ID --output ./downloads/
python download_attachment.py 12345 --all  # Download all from page
```

### list_attachments.py
List attachments on a page.

**Usage:**
```bash
python list_attachments.py 12345
python list_attachments.py 12345 --output json
```

### delete_attachment.py
Remove an attachment.

**Usage:**
```bash
python delete_attachment.py ATTACHMENT_ID
python delete_attachment.py ATTACHMENT_ID --force
```

### update_attachment.py
Replace an attachment file.

**Usage:**
```bash
python update_attachment.py ATTACHMENT_ID --file new_version.pdf
```
