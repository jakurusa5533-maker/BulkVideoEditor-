#!/usr/bin/env bash

echo "=========================================================="
echo "    Google Drive Mount Assistant for Bulk Video Editor"
echo "=========================================================="
echo ""

MOUNT_DIR="$HOME/GoogleDrive"
mkdir -p "$MOUNT_DIR"

# Check if rclone is installed
if ! command -v rclone &> /dev/null; then
    echo "Installing rclone..."
    sudo apt-get update && sudo apt-get install -y rclone
fi

# Check if 'gdrive' remote already exists
if rclone listremotes | grep -q "^gdrive:"; then
    echo "[INFO] Found existing Google Drive configuration ('gdrive:')."
else
    echo "----------------------------------------------------------"
    echo " Setting up Google Drive for the first time:"
    echo " 1. Select 'n' for New remote"
    echo " 2. Type remote name: gdrive"
    echo " 3. Type storage type: drive (or number for Google Drive)"
    echo " 4. Press Enter for client_id and client_secret (default)"
    echo " 5. Select '1' for full access"
    echo " 6. Press Enter for root_folder_id & service_account_file"
    echo " 7. Edit advanced config: 'n'"
    echo " 8. Use web browser: 'n' (rclone will print a link, click it,"
    echo "    sign in, copy the code, and paste it back here)"
    echo " 9. Keep this remote: 'y' and then 'q' to quit."
    echo "----------------------------------------------------------"
    rclone config
fi

# Mount Google Drive
echo ""
echo "[INFO] Mounting Google Drive to $MOUNT_DIR ..."

# Kill any previous mount
fusermount -u "$MOUNT_DIR" 2>/dev/null || true

# Mount in background with caching
rclone mount gdrive: "$MOUNT_DIR" \
    --vfs-cache-mode full \
    --vfs-cache-max-age 24h \
    --buffer-size 64M \
    --dir-cache-time 72h \
    --daemon

sleep 2

# Verify
if mountpoint -q "$MOUNT_DIR" || ls "$MOUNT_DIR" &>/dev/null; then
    mkdir -p "$MOUNT_DIR/Input_Videos"
    mkdir -p "$MOUNT_DIR/Edited_Videos"
    echo "=========================================================="
    echo " [SUCCESS] Google Drive successfully connected!"
    echo " Your Google Drive is mounted at: $MOUNT_DIR"
    echo ""
    echo " Folders available in Bulk Video Editor GUI:"
    echo "   📁 Input Videos : $MOUNT_DIR/Input_Videos"
    echo "   💾 Output Videos: $MOUNT_DIR/Edited_Videos"
    echo "=========================================================="
else
    echo "[WARNING] Mount could not be verified automatically."
    echo "Please check if 'rclone mount gdrive: $MOUNT_DIR --daemon' runs manually."
fi
