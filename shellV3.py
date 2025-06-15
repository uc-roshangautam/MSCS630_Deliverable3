#!/usr/bin/env python3
"""
Enhanced Shell with Memory Management and Process Synchronization
Implements paging system, page replacement algorithms (FIFO/LRU), 
and process synchronization with Producer-Consumer problem simulation
"""

import os
import sys
import threading
import time
import queue
import random
from collections import OrderedDict, deque
from typing import Dict, List, Optional, Set
import subprocess

class Page:
    """Represents a memory page"""
    def __init__(self, page_id: int, process_id: int, data: str = ""):
        self.page_id = page_id
        self.process_id = process_id
        self.data = data
        self.last_accessed = time.time()
        self.load_time = time.time()

class PageFrame:
    """Represents a physical page frame in memory"""
    def __init__(self, frame_id: int):
        self.frame_id = frame_id
        self.page: Optional[Page] = None
        self.is_free = True

class MemoryManager:
    """Manages virtual memory with paging and page replacement algorithms"""
    
    def __init__(self, total_frames: int = 8):
        self.total_frames = total_frames
        self.frames: List[PageFrame] = [PageFrame(i) for i in range(total_frames)]
        self.page_table: Dict[int, Dict[int, Optional[int]]] = {}  # {process_id: {page_id: frame_id}}
        self.page_faults = 0
        self.total_page_requests = 0
        self.replacement_algorithm = "FIFO"  # Default
        self.fifo_queue = deque()  # For FIFO replacement
        self.lru_order = OrderedDict()  # For LRU replacement
        self.lock = threading.Lock()
    
    def allocate_process_memory(self, process_id: int, num_pages: int):
        """Allocate memory pages for a new process"""
        with self.lock:
            if process_id not in self.page_table:
                self.page_table[process_id] = {}
            
            for page_id in range(num_pages):
                self.page_table[process_id][page_id] = None  # Not loaded initially
    
    def access_page(self, process_id: int, page_id: int, data: str = "") -> bool:
        """Access a page, handling page faults if necessary"""
        with self.lock:
            self.total_page_requests += 1
            
            # Check if process exists
            if process_id not in self.page_table:
                print(f"Error: Process {process_id} not found")
                return False
            
            # Check if page exists for process
            if page_id not in self.page_table[process_id]:
                print(f"Error: Page {page_id} not allocated for process {process_id}")
                return False
            
            frame_id = self.page_table[process_id][page_id]
            
            # Page hit - page is already in memory
            if frame_id is not None and not self.frames[frame_id].is_free:
                page = self.frames[frame_id].page
                page.last_accessed = time.time()
                if self.replacement_algorithm == "LRU":
                    # Update LRU order
                    key = (process_id, page_id)
                    if key in self.lru_order:
                        del self.lru_order[key]
                    self.lru_order[key] = time.time()
                print(f"Page hit: Process {process_id}, Page {page_id} -> Frame {frame_id}")
                return True
            
            # Page fault - need to load page into memory
            self.page_faults += 1
            print(f"Page fault: Process {process_id}, Page {page_id}")
            return self._handle_page_fault(process_id, page_id, data)
    
    def _handle_page_fault(self, process_id: int, page_id: int, data: str) -> bool:
        """Handle page fault by loading page into memory"""
        # Find free frame
        free_frame = self._find_free_frame()
        
        if free_frame is None:
            # No free frames, need page replacement
            free_frame = self._page_replacement()
        
        if free_frame is None:
            print("Error: Unable to allocate memory frame")
            return False
        
        # Load page into frame
        page = Page(page_id, process_id, data)
        self.frames[free_frame].page = page
        self.frames[free_frame].is_free = False
        self.page_table[process_id][page_id] = free_frame
        
        # Update replacement algorithm structures
        if self.replacement_algorithm == "FIFO":
            self.fifo_queue.append((process_id, page_id, free_frame))
        elif self.replacement_algorithm == "LRU":
            self.lru_order[(process_id, page_id)] = time.time()
        
        print(f"Page loaded: Process {process_id}, Page {page_id} -> Frame {free_frame}")
        return True
    
    def _find_free_frame(self) -> Optional[int]:
        """Find a free memory frame"""
        for frame in self.frames:
            if frame.is_free:
                return frame.frame_id
        return None
    
    def _page_replacement(self) -> Optional[int]:
        """Perform page replacement using the selected algorithm"""
        if self.replacement_algorithm == "FIFO":
            return self._fifo_replacement()
        elif self.replacement_algorithm == "LRU":
            return self._lru_replacement()
        return None
    
    def _fifo_replacement(self) -> Optional[int]:
        """FIFO page replacement algorithm"""
        if not self.fifo_queue:
            return None
        
        process_id, page_id, frame_id = self.fifo_queue.popleft()
        
        # Remove page from memory
        self.frames[frame_id].page = None
        self.frames[frame_id].is_free = True
        self.page_table[process_id][page_id] = None
        
        print(f"FIFO replacement: Evicted Process {process_id}, Page {page_id} from Frame {frame_id}")
        return frame_id
    
    def _lru_replacement(self) -> Optional[int]:
        """LRU page replacement algorithm"""
        if not self.lru_order:
            return None
        
        # Find least recently used page
        lru_key = min(self.lru_order.keys(), key=lambda k: self.lru_order[k])
        process_id, page_id = lru_key
        
        frame_id = self.page_table[process_id][page_id]
        
        # Remove page from memory
        self.frames[frame_id].page = None
        self.frames[frame_id].is_free = True
        self.page_table[process_id][page_id] = None
        del self.lru_order[lru_key]
        
        print(f"LRU replacement: Evicted Process {process_id}, Page {page_id} from Frame {frame_id}")
        return frame_id
    
    def set_replacement_algorithm(self, algorithm: str):
        """Set the page replacement algorithm"""
        if algorithm.upper() in ["FIFO", "LRU"]:
            self.replacement_algorithm = algorithm.upper()
            print(f"Page replacement algorithm set to: {self.replacement_algorithm}")
        else:
            print("Error: Invalid algorithm. Use 'FIFO' or 'LRU'")
    
    def deallocate_process_memory(self, process_id: int):
        """Deallocate all memory for a process"""
        with self.lock:
            if process_id not in self.page_table:
                return
            
            # Free all frames used by this process
            for page_id, frame_id in self.page_table[process_id].items():
                if frame_id is not None:
                    self.frames[frame_id].page = None
                    self.frames[frame_id].is_free = True
                    
                    # Remove from replacement algorithm structures
                    if self.replacement_algorithm == "LRU":
                        key = (process_id, page_id)
                        if key in self.lru_order:
                            del self.lru_order[key]
            
            # Remove from FIFO queue
            if self.replacement_algorithm == "FIFO":
                self.fifo_queue = deque([item for item in self.fifo_queue 
                                       if item[0] != process_id])
            
            del self.page_table[process_id]
            print(f"Process {process_id} memory deallocated")
    
    def get_memory_status(self):
        """Get current memory status"""
        used_frames = sum(1 for frame in self.frames if not frame.is_free)
        free_frames = self.total_frames - used_frames
        
        print(f"\n=== Memory Status ===")
        print(f"Total Frames: {self.total_frames}")
        print(f"Used Frames: {used_frames}")
        print(f"Free Frames: {free_frames}")
        print(f"Page Faults: {self.page_faults}")
        print(f"Total Page Requests: {self.total_page_requests}")
        if self.total_page_requests > 0:
            fault_rate = (self.page_faults / self.total_page_requests) * 100
            print(f"Page Fault Rate: {fault_rate:.2f}%")
        print(f"Replacement Algorithm: {self.replacement_algorithm}")
        
        print(f"\nFrame Status:")
        for frame in self.frames:
            if frame.is_free:
                print(f"  Frame {frame.frame_id}: FREE")
            else:
                page = frame.page
                print(f"  Frame {frame.frame_id}: Process {page.process_id}, Page {page.page_id}")

class Semaphore:
    """Custom semaphore implementation"""
    def __init__(self, count: int = 1):
        self._count = count
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
    
    def acquire(self):
        with self._condition:
            while self._count <= 0:
                self._condition.wait()
            self._count -= 1
    
    def release(self):
        with self._condition:
            self._count += 1
            self._condition.notify()

class ProducerConsumerSystem:
    """Implementation of Producer-Consumer synchronization problem"""
    
    def __init__(self, buffer_size: int = 5):
        self.buffer = queue.Queue(maxsize=buffer_size)
        self.buffer_size = buffer_size
        self.mutex = threading.Lock()  # Mutex for critical section
        self.empty_slots = Semaphore(buffer_size)  # Available empty slots
        self.full_slots = Semaphore(0)  # Available full slots
        self.producer_count = 0
        self.consumer_count = 0
        self.total_produced = 0
        self.total_consumed = 0
        self.running = False
        self.producers = []
        self.consumers = []
    
    def produce_item(self, producer_id: int):
        """Producer function"""
        while self.running:
            # Create an item
            item = f"Item-{self.total_produced}-P{producer_id}"
            
            # Wait for empty slot
            self.empty_slots.acquire()
            
            # Critical section
            with self.mutex:
                if self.running:  # Check again in case system stopped
                    self.buffer.put(item)
                    self.total_produced += 1
                    print(f"Producer {producer_id} produced: {item} (Buffer size: {self.buffer.qsize()})")
                else:
                    self.empty_slots.release()  # Release if not running
                    break
            
            # Signal that buffer has item
            self.full_slots.release()
            
            # Simulate work
            time.sleep(random.uniform(0.5, 2.0))
    
    def consume_item(self, consumer_id: int):
        """Consumer function"""
        while self.running:
            # Wait for item in buffer
            self.full_slots.acquire()
            
            # Critical section
            with self.mutex:
                if self.running and not self.buffer.empty():
                    item = self.buffer.get()
                    self.total_consumed += 1
                    print(f"Consumer {consumer_id} consumed: {item} (Buffer size: {self.buffer.qsize()})")
                else:
                    self.full_slots.release()  # Release if not running or empty
                    break
            
            # Signal that buffer has empty slot
            self.empty_slots.release()
            
            # Simulate work
            time.sleep(random.uniform(1.0, 3.0))
    
    def start_system(self, num_producers: int = 2, num_consumers: int = 2):
        """Start the producer-consumer system"""
        self.running = True
        self.producer_count = num_producers
        self.consumer_count = num_consumers
        
        print(f"Starting Producer-Consumer system with {num_producers} producers and {num_consumers} consumers")
        print(f"Buffer size: {self.buffer_size}")
        
        # Start producers
        for i in range(num_producers):
            producer = threading.Thread(target=self.produce_item, args=(i,))
            producer.daemon = True
            self.producers.append(producer)
            producer.start()
        
        # Start consumers
        for i in range(num_consumers):
            consumer = threading.Thread(target=self.consume_item, args=(i,))
            consumer.daemon = True
            self.consumers.append(consumer)
            consumer.start()
    
    def stop_system(self):
        """Stop the producer-consumer system"""
        print("Stopping Producer-Consumer system...")
        self.running = False
        
        # Wake up any waiting threads
        for _ in range(self.producer_count):
            self.empty_slots.release()
        for _ in range(self.consumer_count):
            self.full_slots.release()
        
        # Wait for threads to finish
        for producer in self.producers:
            producer.join(timeout=1.0)
        for consumer in self.consumers:
            consumer.join(timeout=1.0)
        
        print(f"System stopped. Total produced: {self.total_produced}, Total consumed: {self.total_consumed}")
        self.producers.clear()
        self.consumers.clear()

class EnhancedShell:
    """Enhanced shell with memory management and process synchronization"""
    
    def __init__(self):
        self.memory_manager = MemoryManager()
        self.producer_consumer = ProducerConsumerSystem()
        self.process_counter = 1
        self.running = True
        
        # Built-in commands
        self.commands = {
            'help': self.help_command,
            'exit': self.exit_command,
            'clear': self.clear_command,
            'mem_status': self.memory_status_command,
            'mem_alloc': self.memory_allocate_command,
            'mem_access': self.memory_access_command,
            'mem_dealloc': self.memory_deallocate_command,
            'mem_algorithm': self.memory_algorithm_command,
            'pc_start': self.producer_consumer_start_command,
            'pc_stop': self.producer_consumer_stop_command,
            'pc_status': self.producer_consumer_status_command,
            'simulate_workload': self.simulate_workload_command,
            'compare_algorithms': self.compare_algorithms_command,
        }
    
    def help_command(self, args):
        """Display help information"""
        print("\n=== Enhanced Shell Commands ===")
        print("Memory Management:")
        print("  mem_status                     - Show memory status")
        print("  mem_alloc <pid> <pages>        - Allocate memory for process")
        print("  mem_access <pid> <page> [data] - Access a page")
        print("  mem_dealloc <pid>              - Deallocate process memory")
        print("  mem_algorithm <FIFO|LRU>       - Set page replacement algorithm")
        print("\nProcess Synchronization:")
        print("  pc_start [producers] [consumers] - Start producer-consumer system")
        print("  pc_stop                        - Stop producer-consumer system")
        print("  pc_status                      - Show producer-consumer status")
        print("\nSimulation:")
        print("  simulate_workload <algorithm>  - Simulate memory workload")
        print("  compare_algorithms             - Compare FIFO vs LRU performance")
        print("\nGeneral:")
        print("  help                           - Show this help")
        print("  clear                          - Clear screen")
        print("  exit                           - Exit shell")
    
    def exit_command(self, args):
        """Exit the shell"""
        self.producer_consumer.stop_system()
        print("Goodbye!")
        self.running = False
    
    def clear_command(self, args):
        """Clear the screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def memory_status_command(self, args):
        """Show memory status"""
        self.memory_manager.get_memory_status()
    
    def memory_allocate_command(self, args):
        """Allocate memory for a process"""
        if len(args) < 2:
            print("Usage: mem_alloc <process_id> <num_pages>")
            return
        
        try:
            process_id = int(args[0])
            num_pages = int(args[1])
            self.memory_manager.allocate_process_memory(process_id, num_pages)
            print(f"Allocated {num_pages} pages for process {process_id}")
        except ValueError:
            print("Error: Invalid arguments. Use integers for process_id and num_pages")
    
    def memory_access_command(self, args):
        """Access a memory page"""
        if len(args) < 2:
            print("Usage: mem_access <process_id> <page_id> [data]")
            return
        
        try:
            process_id = int(args[0])
            page_id = int(args[1])
            data = args[2] if len(args) > 2 else f"Data-{process_id}-{page_id}"
            self.memory_manager.access_page(process_id, page_id, data)
        except ValueError:
            print("Error: Invalid arguments. Use integers for process_id and page_id")
    
    def memory_deallocate_command(self, args):
        """Deallocate memory for a process"""
        if len(args) < 1:
            print("Usage: mem_dealloc <process_id>")
            return
        
        try:
            process_id = int(args[0])
            self.memory_manager.deallocate_process_memory(process_id)
        except ValueError:
            print("Error: Invalid process_id. Use an integer")
    
    def memory_algorithm_command(self, args):
        """Set page replacement algorithm"""
        if len(args) < 1:
            print("Usage: mem_algorithm <FIFO|LRU>")
            return
        
        self.memory_manager.set_replacement_algorithm(args[0])
    
    def producer_consumer_start_command(self, args):
        """Start producer-consumer system"""
        num_producers = int(args[0]) if len(args) > 0 else 2
        num_consumers = int(args[1]) if len(args) > 1 else 2
        
        if self.producer_consumer.running:
            print("Producer-Consumer system is already running. Stop it first.")
            return
        
        self.producer_consumer.start_system(num_producers, num_consumers)
    
    def producer_consumer_stop_command(self, args):
        """Stop producer-consumer system"""
        if not self.producer_consumer.running:
            print("Producer-Consumer system is not running.")
            return
        
        self.producer_consumer.stop_system()
    
    def producer_consumer_status_command(self, args):
        """Show producer-consumer status"""
        print(f"\n=== Producer-Consumer Status ===")
        print(f"Running: {self.producer_consumer.running}")
        print(f"Buffer size: {self.producer_consumer.buffer_size}")
        print(f"Current buffer items: {self.producer_consumer.buffer.qsize()}")
        print(f"Total produced: {self.producer_consumer.total_produced}")
        print(f"Total consumed: {self.producer_consumer.total_consumed}")
        print(f"Producers: {self.producer_consumer.producer_count}")
        print(f"Consumers: {self.producer_consumer.consumer_count}")
    
    def simulate_workload_command(self, args):
        """Simulate memory workload"""
        if len(args) < 1:
            print("Usage: simulate_workload <FIFO|LRU>")
            return
        
        algorithm = args[0].upper()
        if algorithm not in ["FIFO", "LRU"]:
            print("Error: Algorithm must be FIFO or LRU")
            return
        
        print(f"\n=== Simulating Memory Workload with {algorithm} ===")
        
        # Reset memory manager
        self.memory_manager = MemoryManager()
        self.memory_manager.set_replacement_algorithm(algorithm)
        
        # Allocate memory for 3 processes
        for pid in range(1, 4):
            self.memory_manager.allocate_process_memory(pid, 4)
        
        # Simulate memory access pattern
        access_pattern = [
            (1, 0), (1, 1), (2, 0), (3, 0), (1, 2), (2, 1),
            (3, 1), (1, 3), (2, 2), (3, 2), (1, 0), (2, 3),
            (3, 3), (1, 1), (2, 0), (3, 0)
        ]
        
        print(f"Executing access pattern: {access_pattern}")
        for pid, page_id in access_pattern:
            self.memory_manager.access_page(pid, page_id)
            time.sleep(0.1)  # Small delay for visualization
        
        self.memory_manager.get_memory_status()
    
    def compare_algorithms_command(self, args):
        """Compare FIFO vs LRU algorithms"""
        print("\n=== Comparing Page Replacement Algorithms ===")
        
        # Test pattern
        access_pattern = [
            (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5),
            (1, 0), (1, 1), (1, 2), (1, 3), (1, 0), (1, 1)
        ]
        
        results = {}
        
        for algorithm in ["FIFO", "LRU"]:
            print(f"\n--- Testing {algorithm} ---")
            
            # Reset memory manager
            self.memory_manager = MemoryManager(total_frames=4)
            self.memory_manager.set_replacement_algorithm(algorithm)
            self.memory_manager.allocate_process_memory(1, 6)
            
            # Execute access pattern
            for pid, page_id in access_pattern:
                self.memory_manager.access_page(pid, page_id)
            
            results[algorithm] = {
                'page_faults': self.memory_manager.page_faults,
                'total_requests': self.memory_manager.total_page_requests,
                'fault_rate': (self.memory_manager.page_faults / self.memory_manager.total_page_requests) * 100
            }
        
        # Compare results
        print(f"\n=== Algorithm Comparison Results ===")
        for algorithm, stats in results.items():
            print(f"{algorithm}:")
            print(f"  Page Faults: {stats['page_faults']}")
            print(f"  Total Requests: {stats['total_requests']}")
            print(f"  Fault Rate: {stats['fault_rate']:.2f}%")
        
        if results['FIFO']['fault_rate'] < results['LRU']['fault_rate']:
            print("FIFO performed better for this workload")
        elif results['LRU']['fault_rate'] < results['FIFO']['fault_rate']:
            print("LRU performed better for this workload")
        else:
            print("Both algorithms performed equally")
    
    def execute_command(self, command_line):
        """Execute a command"""
        parts = command_line.strip().split()
        if not parts:
            return
        
        command = parts[0]
        args = parts[1:]
        
        if command in self.commands:
            try:
                self.commands[command](args)
            except Exception as e:
                print(f"Error executing command: {e}")
        else:
            # Try to execute as system command
            try:
                subprocess.run(parts, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Command failed with exit code {e.returncode}")
            except FileNotFoundError:
                print(f"Command not found: {command}")
    
    def run(self):
        """Main shell loop"""
        print("Enhanced Shell with Memory Management and Process Synchronization")
        print("Type 'help' for available commands")
        
        while self.running:
            try:
                command_line = input("enhanced_shell> ")
                self.execute_command(command_line)
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit")
            except EOFError:
                break

if __name__ == "__main__":
    shell = EnhancedShell()
    shell.run()