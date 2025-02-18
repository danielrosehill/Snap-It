#!/usr/bin/env python3
import sys
import subprocess
import logging
import re

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QWidget, 
    QVBoxLayout,
    QLineEdit, 
    QPushButton,
    QMessageBox,
    QLabel,
    QStatusBar
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

class SnapperGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Snap-It")
        self.setFixedSize(600, 250)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Add description label
        desc_label = QLabel("A really simple GUI for quickly creating on-demand\nSnapper snapshots in OpenSUSE")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)
        
        # Create comment input field
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Enter snapshot description...")
        self.comment_input.setMinimumHeight(35)
        layout.addWidget(self.comment_input)
        
        # Create snapshot button
        self.snap_button = QPushButton("Take Snapshot")
        self.snap_button.clicked.connect(self.take_snapshot)
        self.snap_button.setMinimumHeight(35)
        layout.addWidget(self.snap_button)
        
        # Add status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Center the window
        self.center_window()
        
    def center_window(self):
        frame_geometry = self.frameGeometry()
        screen = QApplication.primaryScreen()
        center_point = screen.availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        
    def take_snapshot(self):
        comment = self.comment_input.text().strip()
        
        if not comment:
            QMessageBox.warning(
                self,
                "Warning",
                "Please enter a description for the snapshot."
            )
            return
            
        try:
            self.status_bar.showMessage("Creating snapshot...")
            self.snap_button.setEnabled(False)
            
            # First create the snapshot and get its number
            logger.debug("Creating snapshot...")
            create_result = subprocess.run(
                ["sudo", "snapper", "create", "--description", comment, "--type", "single", "--print-number"],
                check=True,
                capture_output=True,
                text=True
            )
            
            snapshot_num = create_result.stdout.strip()
            logger.debug(f"Got snapshot number: {snapshot_num}")
            
            if not snapshot_num:
                raise Exception("Failed to get snapshot number")
            
            # Get the subvolume path
            logger.debug("Getting subvolume path...")
            config_result = subprocess.run(
                ["sudo", "snapper", "get-config"],
                check=True,
                capture_output=True,
                text=True
            )
            
            subvolume = None
            for line in config_result.stdout.split('\n'):
                if 'SUBVOLUME' in line:
                    # Split by │ character (note: this is not a regular pipe)
                    parts = line.split('│')
                    if len(parts) >= 2:
                        subvolume = parts[1].strip()
                        break
            
            logger.debug(f"Found subvolume: {subvolume}")
            
            if not subvolume:
                raise Exception("Failed to get subvolume path")
                
            snapshot_path = f"{subvolume}/.snapshots/{snapshot_num}/snapshot"
            logger.debug(f"Snapshot path: {snapshot_path}")
            
            # Get snapshot details
            logger.debug("Getting snapshot details...")
            details_result = subprocess.run(
                ["sudo", "snapper", "list", "-t", "single"],
                check=True,
                capture_output=True,
                text=True
            )
            
            size = "Unknown"
            for line in details_result.stdout.split('\n'):
                if line.strip().startswith(snapshot_num):
                    size_match = re.search(r'(\d+\.?\d*\s*[KMGTP]?i?B)', line)
                    if size_match:
                        size = size_match.group(1)
                    break
            
            logger.debug(f"Got size: {size}")
            
            success_msg = (
                f"Snapshot #{snapshot_num} created successfully!\n\n"
                f"Size: {size}\n"
                f"Location: {snapshot_path}"
            )
            
            logger.debug(f"Success message: {success_msg}")
            self.status_bar.showMessage("Snapshot created successfully")
            QMessageBox.information(
                self,
                "Success",
                success_msg
            )
            
            self.comment_input.clear()
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to create snapshot. Error: {e.stderr}"
            logger.error(error_msg)
            self.status_bar.showMessage("Error creating snapshot")
            QMessageBox.critical(
                self,
                "Error",
                error_msg
            )
        except Exception as e:
            error_msg = f"An unexpected error occurred: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.status_bar.showMessage("Error creating snapshot")
            QMessageBox.critical(
                self,
                "Error",
                error_msg
            )
        finally:
            self.snap_button.setEnabled(True)

def main():
    app = QApplication(sys.argv)
    
    # Set fusion style for better default appearance
    app.setStyle("Fusion")
    
    window = SnapperGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
