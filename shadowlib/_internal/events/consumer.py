"""
Inotify-based event consumer for RuneLite events.

Watches /dev/shm/runelite_doorbell using inotify for instant event notifications.
Processes ring buffer and latest-state channels, updates cache.
Runs in background thread.

Requirements:
- Linux with inotify support (required, no fallback)
- RuneLite with ShadowBot plugin running (creates doorbell)
"""

import glob
import os
import threading
import time
from collections import defaultdict
from typing import Optional

import msgpack
from inotify_simple import INotify
from inotify_simple import flags as inotify_flags

from .channels import (
    DOORBELL_PATH,
    LATEST_STATE_CHANNELS,
    RING_BUFFER_CHANNELS,
    SHM_DIR,
)


class EventConsumer:
    """
    Consumes events from /dev/shm using inotify doorbell pattern.

    Architecture:
    - Watches doorbell file with inotify (zero CPU when idle)
    - Wakes instantly when doorbell is rung
    - Processes all pending ring buffer and latest-state events
    - Updates cache with event data
    - Runs in background daemon thread
    """

    def __init__(self, cache, warn_on_gaps: bool = True):
        """
        Initialize event consumer.

        Args:
            cache: EventCache instance to update
            warn_on_gaps: Warn when ring buffer sequence gaps detected
        """
        self.cache = cache
        self.warn_on_gaps = warn_on_gaps

        # Tracking state
        self.last_seq = defaultdict(int)  # Last processed sequence per channel
        self.last_state_mtime = defaultdict(float)  # Last mtime per state channel

        # Thread control
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # Inotify setup
        self.inotify: Optional[INotify] = None
        self._setupInotify()

    def _setupInotify(self) -> None:
        """Setup inotify watch on doorbell file."""
        self.inotify = INotify()

        # Check if doorbell exists
        if not os.path.exists(DOORBELL_PATH):
            print(f"⚠️  Doorbell not found at {DOORBELL_PATH}")
            print("   Waiting for Java plugin to create it...")
            # Wait up to 5 seconds for doorbell to appear
            for _ in range(50):
                if os.path.exists(DOORBELL_PATH):
                    break
                time.sleep(0.1)

        if not os.path.exists(DOORBELL_PATH):
            raise FileNotFoundError(
                f"Doorbell not found at {DOORBELL_PATH}. "
                f"Make sure RuneLite is running with ShadowBot plugin."
            )

        # Watch for modifications and close-write events
        self.inotify.add_watch(DOORBELL_PATH, inotify_flags.MODIFY | inotify_flags.CLOSE_WRITE)
        print(f"✅ Watching doorbell: {DOORBELL_PATH}")

    def start(self) -> bool:
        """
        Start background event consumer thread.

        Returns:
            True if started successfully
        """
        if self.running:
            print("⚠️  Event consumer already running")
            return False

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True, name="EventConsumer")
        self.thread.start()

        print("✅ Event consumer started (inotify mode)")
        return True

    def stop(self) -> None:
        """Stop event consumer thread."""
        if not self.running:
            return

        print("🛑 Stopping event consumer...")
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

        if self.inotify:
            self.inotify.close()

        print("✅ Event consumer stopped")

    def _run(self) -> None:
        """Main event loop - runs in background thread."""
        print("🔄 Event consumer loop started")
        print(f"   Ring buffer channels: {', '.join(RING_BUFFER_CHANNELS)}")
        print(f"   Latest-state channels: {', '.join(LATEST_STATE_CHANNELS)}")
        print()

        while self.running:
            try:
                # Block here until doorbell rings (zero CPU usage!)
                events = self.inotify.read(timeout=1000)  # 1s timeout for clean shutdown

                if events:
                    # Doorbell was rung! Process all channels
                    self._processAllChannels()

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error in event loop: {e}")
                import traceback

                traceback.print_exc()
                time.sleep(1)

    def _processAllChannels(self) -> None:
        """Process all ring buffer and latest-state channels."""
        start_time = time.time()
        total_events = 0

        # Process ring buffer channels (guaranteed delivery)
        for channel in RING_BUFFER_CHANNELS:
            count = self._processRingBuffer(channel)
            total_events += count

        # Process latest-state channels (current state only)
        for channel in LATEST_STATE_CHANNELS:
            self._processLatestState(channel)

        # Log if we processed more than 10 events
        if total_events > 10:
            elapsed_ms = (time.time() - start_time) * 1000
            per_event_us = (elapsed_ms * 1000) / total_events if total_events > 0 else 0
            print(
                f"✅ Cleared {total_events} events in {elapsed_ms:.1f} ms ({per_event_us:.0f}μs/event)"
            )

    def _processRingBuffer(self, channel: str) -> int:
        """
        Process ring buffer events for a channel.

        Files: /dev/shm/{channel}.{seq}

        Args:
            channel: Channel name

        Returns:
            Number of events processed
        """
        pattern = f"{SHM_DIR}/{channel}.*"
        files = sorted(
            glob.glob(pattern),
            key=lambda x: int(x.split(".")[-1]) if x.split(".")[-1].isdigit() else 0,
        )

        events_processed = 0

        for filepath in files:
            try:
                # Extract sequence number
                filename = os.path.basename(filepath)
                parts = filename.split(".")
                if len(parts) < 2 or not parts[-1].isdigit():
                    continue

                seq = int(parts[-1])

                # Skip if already processed
                if seq <= self.last_seq[channel]:
                    os.remove(filepath)
                    continue

                # Read and deserialize event
                with open(filepath, "rb") as f:
                    event = msgpack.unpackb(f.read(), raw=False, strict_map_key=False)

                # Verify sequence continuity
                expected_seq = self.last_seq[channel] + 1
                if seq != expected_seq and self.last_seq[channel] > 0:
                    if self.warn_on_gaps:
                        gap_size = seq - expected_seq
                        print(
                            f"⚠️  [{channel}] Gap detected! Expected {expected_seq}, got {seq} (missed {gap_size})"
                        )

                # Store event in cache
                # print(f"🔔 [{channel}] Processing event seq={seq} with event {event}")
                self.cache.addEvent(channel, event)

                # Update sequence tracker
                self.last_seq[channel] = seq
                events_processed += 1

                # Delete processed event
                os.remove(filepath)

            except Exception as e:
                print(f"❌ Error processing {filepath}: {e}")

        return events_processed

    def _processLatestState(self, channel: str) -> bool:
        """
        Process latest-state event for a channel.

        Files: /dev/shm/{channel}

        Args:
            channel: Channel name

        Returns:
            True if state was updated
        """
        filepath = f"{SHM_DIR}/{channel}"

        try:
            if not os.path.exists(filepath):
                return False

            # Check if file was modified since last read
            stat = os.stat(filepath)
            current_mtime = stat.st_mtime

            # Skip if file hasn't changed
            if current_mtime <= self.last_state_mtime[channel]:
                return False

            # Update modification time tracker
            self.last_state_mtime[channel] = current_mtime

            # Read and deserialize state
            with open(filepath, "rb") as f:
                state = msgpack.unpackb(f.read(), raw=False, strict_map_key=False)

            # Update cache - all latest-state events use same method now
            self.cache.addEvent(channel, state)

            return True

        except Exception as e:
            print(f"❌ Error reading {filepath}: {e}")
            return False
