"""
extract_pst.py
Extracts emails from a PST file using Outlook COM automation (Windows only).
Outputs a JSON file with metadata + body preview for each email.

Requirements:
    pip install pywin32

Usage:
    python extract_pst.py "C:\\path\\to\\your\\file.pst"

NOTE: Outlook must be installed. The script opens the PST read-only.
"""

import json
import os
import sys
import time
from datetime import datetime

import win32com.client

# How many chars of body text to keep per email (~500 words ≈ 3000 chars)
BODY_PREVIEW_LENGTH = 3000

# Save progress every N emails
CHECKPOINT_EVERY = 1000


def extract_emails(pst_path):
    pst_path = os.path.abspath(pst_path)
    if not os.path.exists(pst_path):
        print(f"File not found: {pst_path}")
        sys.exit(1)

    print(f"Opening Outlook and loading PST: {pst_path}")
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")

    # Add PST file to Outlook profile
    outlook.AddStore(pst_path)

    # Find the added store — it's the last root folder
    root = None
    for i in range(outlook.Folders.Count, 0, -1):
        folder = outlook.Folders.Item(i)
        # Match by checking if it's the PST we just added
        try:
            store_path = folder.StoreID
            root = folder
            break
        except Exception:
            continue

    if root is None:
        print("Could not find the PST store. Try opening the PST manually in Outlook first.")
        sys.exit(1)

    print(f"Found PST root: {root.Name}")
    print(f"Scanning folders...")

    emails = []
    errors = 0
    start_time = time.time()

    def process_folder(folder, folder_path=""):
        nonlocal errors
        current_path = f"{folder_path}/{folder.Name}" if folder_path else folder.Name

        try:
            items = folder.Items
            count = items.Count
            if count > 0:
                print(f"  {current_path}: {count} items")

            for i in range(1, count + 1):
                try:
                    item = items.Item(i)
                    # Only process mail items (class 43 = olMail)
                    if item.Class != 43:
                        continue

                    body_text = ""
                    try:
                        body_text = (item.Body or "")[:BODY_PREVIEW_LENGTH]
                    except Exception:
                        pass

                    # Extract recipients (To and CC)
                    to_str = ""
                    cc_str = ""
                    try:
                        to_str = str(getattr(item, "To", "") or "")
                    except Exception:
                        pass
                    try:
                        cc_str = str(getattr(item, "CC", "") or "")
                    except Exception:
                        pass

                    email_data = {
                        "subject": str(getattr(item, "Subject", "") or ""),
                        "from_name": str(getattr(item, "SenderName", "") or ""),
                        "from_email": str(getattr(item, "SenderEmailAddress", "") or ""),
                        "to": to_str,
                        "cc": cc_str,
                        "date": "",
                        "is_read": bool(getattr(item, "UnRead", True) == False),
                        "importance": int(getattr(item, "Importance", 1)),
                        "has_attachments": bool(getattr(item, "Attachments", None) and item.Attachments.Count > 0),
                        "folder": current_path,
                        "preview": body_text,
                    }

                    try:
                        recv = item.ReceivedTime
                        email_data["date"] = recv.strftime("%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        pass

                    emails.append(email_data)

                    if len(emails) % CHECKPOINT_EVERY == 0:
                        elapsed = time.time() - start_time
                        rate = len(emails) / elapsed * 60
                        print(f"    ... {len(emails)} emails extracted ({rate:.0f}/min)")

                except Exception as e:
                    errors += 1
                    if errors <= 10:
                        print(f"    Error on item {i}: {e}")

        except Exception as e:
            print(f"  Could not access folder {current_path}: {e}")

        # Recurse into subfolders
        try:
            for j in range(1, folder.Folders.Count + 1):
                subfolder = folder.Folders.Item(j)
                process_folder(subfolder, current_path)
        except Exception:
            pass

    process_folder(root)

    # Remove the PST from Outlook when done
    try:
        outlook.RemoveStore(root)
        print("PST removed from Outlook profile.")
    except Exception:
        print("Note: could not auto-remove PST from Outlook. Remove it manually if needed.")

    return emails, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_pst.py <path_to_pst_file>")
        sys.exit(1)

    pst_path = sys.argv[1]
    print("=== PST Email Extractor (read-only) ===\n")

    emails, errors = extract_emails(pst_path)

    print(f"\nExtracted {len(emails)} emails ({errors} errors)")

    # Save to JSON
    output_file = "extracted_emails.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(emails, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize(output_file) / 1024 / 1024
    print(f"Saved to {output_file} ({size_mb:.1f} MB)")

    # Quick stats
    print(f"\n--- Quick Stats ---")
    unread = sum(1 for e in emails if not e["is_read"])
    print(f"Total: {len(emails)}  |  Unread: {unread}  |  Read: {len(emails) - unread}")

    senders = {}
    for e in emails:
        addr = e["from_email"].lower()
        senders[addr] = senders.get(addr, 0) + 1

    print(f"\nTop 20 senders:")
    for addr, count in sorted(senders.items(), key=lambda x: -x[1])[:20]:
        print(f"  {count:5d}  {addr}")

    # Folder breakdown
    folders = {}
    for e in emails:
        f = e["folder"]
        folders[f] = folders.get(f, 0) + 1

    print(f"\nFolders:")
    for f, count in sorted(folders.items(), key=lambda x: -x[1]):
        print(f"  {count:5d}  {f}")


if __name__ == "__main__":
    main()