---
name: confluence-attachment
description: Manage file attachments - upload, download, list, and delete attachments. ALWAYS use when user wants to work with files on pages.
triggers:
  - attach
  - attachment
  - upload file
  - download file
  - upload attachment
  - download attachment
  - file
  - files
---

# Confluence Attachment Skill

Manage file attachments on Confluence pages.

---

## ⚠️ PRIMARY USE CASE

**This skill manages files attached to Confluence pages.** Use for:
- Uploading files to pages
- Downloading attachments
- Listing files on a page
- Deleting attachments

---

## When to Use / When NOT to Use

| Use This Skill | Use Instead |
|----------------|-------------|
| Upload/download files | - |
| List page attachments | - |
| Delete attachments | - |
| Create/edit pages | `confluence-page` |
| Search for content | `confluence-search` |

---

## Risk Levels

| Operation | Risk | Notes |
|-----------|------|-------|
| List/download | - | Read-only |
| Upload | - | Can be deleted |
| Update | ⚠️ | Replaces existing file |
| Delete | ⚠️⚠️ | **No recovery** |

---

## CLI Commands

### confluence-as attachment upload
Upload a file to a page.

**Usage:**
```bash
confluence-as attachment upload PAGE_ID FILE_PATH
confluence-as attachment upload 12345 report.pdf
confluence-as attachment upload 12345 image.png --comment "Screenshot"
confluence-as attachment upload 12345 data.csv --output json
```

**Options:**
- `--comment` - Comment describing the attachment
- `--output, -o` - Output format: `text` (default) or `json`

### confluence-as attachment download
Download an attachment.

**Usage:**
```bash
confluence-as attachment download ATTACHMENT_ID --output ./downloads/
confluence-as attachment download att123456 --output myfile.pdf
confluence-as attachment download 12345 --all --output ./downloads/  # Download all from page
```

**Options:**
- `--output, -o` - Output file or directory (default: current directory)
- `--all, -a` - Download all attachments from a page (the ID argument is a page ID)

### confluence-as attachment list
List attachments on a page.

**Usage:**
```bash
confluence-as attachment list 12345
confluence-as attachment list 12345 --output json
confluence-as attachment list 12345 --output table
confluence-as attachment list 12345 --media-type application/pdf
confluence-as attachment list 12345 --limit 50
```

**Options:**
- `--output, -o` - Output format: `text`, `json`, or `table`
- `--media-type, -m` - Filter by media type (e.g., `application/pdf`)
- `--limit, -l` - Maximum number of results (default 25, max 250)

### confluence-as attachment delete
Remove an attachment.

**Usage:**
```bash
confluence-as attachment delete ATTACHMENT_ID
confluence-as attachment delete ATTACHMENT_ID --force
confluence-as attachment delete ATTACHMENT_ID --purge --force
```

**Options:**
- `--force`, `-f` - Skip confirmation prompt
- `--purge` - Permanently delete (otherwise moves to trash)

### confluence-as attachment update
Replace an attachment file.

**Usage:**
```bash
confluence-as attachment update ATTACHMENT_ID FILE_PATH
confluence-as attachment update att123456 new_version.pdf
confluence-as attachment update att123456 updated.docx --comment "Updated content"
confluence-as attachment update att123456 report.pdf --output json
```

**Options:**
- `--comment` - Comment describing the update
- `--output, -o` - Output format: `text` (default) or `json`
