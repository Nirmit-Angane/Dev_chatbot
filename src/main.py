import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import os
import subprocess
import platform
from datetime import datetime
import webbrowser
import shutil
import json

try:
    from groq import Groq
    from dotenv import load_dotenv
    load_dotenv()
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("Groq library not available. AI features will be limited.")

try:
    import pyautogui
    SCREENSHOT_AVAILABLE = True
except ImportError:
    SCREENSHOT_AVAILABLE = False
    print("pyautogui not available. Screenshot feature disabled.")


class BroDevAI:
    def __init__(self):
        self.history = []
        self.history_file = "chat_history.json"
        self.load_history()
        
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # Remove window decorations
        self.setup_window()
        
        # Initialize UI components
        self.ui = UIComponents(self)
        self.ui.create_widgets()
        
        # Initialize Groq client if available
        self.ai_available = False
        if GROQ_AVAILABLE:
            try:
                api_key = os.getenv('GROQ_API_KEY')
                self.groq_client = Groq(api_key=api_key)
                self.ai_available = True
            except Exception as e:
                print(f"Failed to initialize Groq client: {e}")
        
        self.is_typing = False
        self.conversation_history = []
        self.current_directory = os.getcwd()
        
        # Initialize typing indicator position
        self.typing_pos = None
        
        # Hover functionality variables
        self.is_hidden = True  # Start hidden
        self.hide_timer = None
        self.show_timer = None
        self.animation_in_progress = False
        self.mouse_monitoring = True
        
        # Slash commands registry
        self.slash_commands = {
            "/help": self.show_help,
            "/open_web": self.open_web,
            "/open_app": self.open_app,
            "/open_folder": self.open_folder,
            "/search_files": self.search_files_command,
            "/create_file": self.create_file_command,
            "/system_info": self.system_info,
            "/clear": self.clear_chat,
            "/time": self.show_time,
            "/weather": self.get_weather,
            "/calc": self.calculate,
            "/history": self.show_history,
            "/todo": self.todo_command,
            "/note": self.quick_note,
            "/screenshot": self.take_screenshot,
            "/backup": self.backup_files,
        }
        
        # Create hover zone after window setup
        self.root.after(100, self.create_hover_zone)

    def load_history(self):
        """Load chat history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            self.history = []

    def save_history(self):
        """Save chat history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history[-100:], f, indent=2)  # Keep only last 100 entries
        except Exception as e:
            print(f"Error saving history: {e}")

    def add_to_history(self, message, sender):
        """Add message to history"""
        self.history.append({
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'sender': sender,
            'message': message[:500]  # Limit message length
        })
        self.save_history()

    def show_history(self, args=""):
        """Display chat history"""
        if not self.history:
            self.display_message("No history available", "system")
            return
        
        history_text = "Chat History (Last 10 messages):\n\n"
        for item in self.history[-10:]:  # Show last 10 items
            history_text += f"[{item['timestamp']}] {item['sender']}: {item['message'][:100]}...\n\n"
        
        self.display_message(history_text, "command")

    def setup_window(self):
        """Configure the main window with dark theme"""
        # Window dimensions
        window_width = 450
        window_height = 700
        
        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        self.y = (self.screen_height - window_height) // 2
        
        # Position settings - only 10 pixels visible when hidden
        self.hidden_x = self.screen_width - 10
        self.visible_x = self.screen_width - window_width
        
        # Configure window
        self.root.geometry(f"{window_width}x{window_height}+{self.hidden_x}+{self.y}")
        self.root.configure(bg="#1a1a1a")
        self.root.attributes('-topmost', True)  # Keep on top
        
        # Bind mouse events for hover functionality
        self.root.bind("<Enter>", self.on_mouse_enter)
        self.root.bind("<Leave>", self.on_mouse_leave)
        
        # Make window draggable
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.on_move)
        self._drag_data = {"x": 0, "y": 0}
    
    def create_hover_zone(self):
        """Create an invisible window at the screen edge for hover detection"""
        try:
            self.hover_zone = tk.Toplevel(self.root)
            self.hover_zone.overrideredirect(True)
            self.hover_zone.attributes('-topmost', True)
            self.hover_zone.configure(bg='black')
            self.hover_zone.attributes('-alpha', 0.01)  # Nearly invisible
            
            # Position at the very edge of the screen
            hover_width = 3
            hover_x = self.screen_width - hover_width
            self.hover_zone.geometry(f"{hover_width}x{self.screen_height}+{hover_x}+0")
            
            # Bind hover events to the zone
            self.hover_zone.bind("<Enter>", self.on_hover_zone_enter)
            
            # Start the mouse monitoring
            self.monitor_mouse_position()
            
        except Exception as e:
            print(f"Error creating hover zone: {e}")
            # Fallback to simple monitoring
            self.monitor_mouse_position()
    
    def monitor_mouse_position(self):
        """Continuously monitor mouse position"""
        if not self.mouse_monitoring:
            return
            
        try:
            mouse_x = self.root.winfo_pointerx()
            edge_threshold = 50
            
            # Show window when mouse is near right edge
            if mouse_x >= self.screen_width - edge_threshold:
                if self.is_hidden and not self.animation_in_progress:
                    self.cancel_hide_timer()
                    self.show_window()
            else:
                # Hide window when mouse moves away
                if not self.is_hidden and not self.animation_in_progress:
                    if not self.is_mouse_over_main_window():
                        if not self.hide_timer:
                            self.hide_timer = self.root.after(2000, self.hide_window)
            
        except Exception as e:
            pass  # Ignore errors in mouse monitoring
        
        if self.mouse_monitoring:
            self.root.after(200, self.monitor_mouse_position)
    
    def is_mouse_over_main_window(self):
        """Check if mouse is over the main window"""
        try:
            mouse_x = self.root.winfo_pointerx()
            mouse_y = self.root.winfo_pointery()
            win_x = self.root.winfo_rootx()
            win_y = self.root.winfo_rooty()
            win_width = self.root.winfo_width()
            win_height = self.root.winfo_height()
            
            return (win_x <= mouse_x <= win_x + win_width and 
                   win_y <= mouse_y <= win_y + win_height)
        except:
            return False
    
    def cancel_hide_timer(self):
        """Cancel any pending hide timer"""
        if self.hide_timer:
            self.root.after_cancel(self.hide_timer)
            self.hide_timer = None
    
    def on_hover_zone_enter(self, event=None):
        """Show window when mouse enters the hover zone"""
        self.cancel_hide_timer()
        if self.is_hidden and not self.animation_in_progress:
            self.show_window()
    
    def on_mouse_enter(self, event=None):
        """Show window when mouse enters main window"""
        self.cancel_hide_timer()
    
    def on_mouse_leave(self, event=None):
        """Handle mouse leaving main window"""
        pass
    
    def show_window(self):
        """Animate window sliding out from right edge"""
        if not self.is_hidden or self.animation_in_progress:
            return
        
        self.animation_in_progress = True
        self.cancel_hide_timer()
        
        current_x = self.root.winfo_x()
        target_x = self.visible_x
        steps = 20
        delay = 15
        
        def animate_step(step):
            if step <= steps and self.animation_in_progress:
                progress = step / steps
                # Ease out animation
                eased_progress = 1 - pow(1 - progress, 3)
                new_x = int(current_x + (target_x - current_x) * eased_progress)
                
                try:
                    self.root.geometry(f"450x700+{new_x}+{self.y}")
                    self.root.update()
                except:
                    pass
                
                if step < steps:
                    self.root.after(delay, lambda: animate_step(step + 1))
                else:
                    self.animation_in_progress = False
                    self.is_hidden = False
            else:
                self.animation_in_progress = False
                self.is_hidden = False
        
        animate_step(1)
    
    def hide_window(self):
        """Animate window sliding back to right edge"""
        if self.is_hidden or self.animation_in_progress:
            return
        
        self.animation_in_progress = True
        self.hide_timer = None
        
        current_x = self.root.winfo_x()
        target_x = self.hidden_x
        steps = 20
        delay = 15
        
        def animate_step(step):
            if step <= steps and self.animation_in_progress:
                progress = step / steps
                # Ease in animation
                eased_progress = progress * progress * progress
                new_x = int(current_x + (target_x - current_x) * eased_progress)
                
                try:
                    self.root.geometry(f"450x700+{new_x}+{self.y}")
                    self.root.update()
                except:
                    pass
                
                if step < steps:
                    self.root.after(delay, lambda: animate_step(step + 1))
                else:
                    self.animation_in_progress = False
                    self.is_hidden = True
            else:
                self.animation_in_progress = False
                self.is_hidden = True
        
        animate_step(1)
    
    def display_message(self, message, tag):
        """Display a message in the chat"""
        try:
            self.ui.chat_display.config(state="normal")
            timestamp = datetime.now().strftime("%H:%M")
            
            if tag == "user":
                formatted_message = f"[{timestamp}] You: {message}\n\n"
                self.add_to_history(message, "You")
            elif tag == "ai":
                formatted_message = f"[{timestamp}] BroDev AI: {message}\n\n"
                self.add_to_history(message, "BroDev AI")
            elif tag == "system":
                formatted_message = f"[{timestamp}] System: {message}\n\n"
                self.add_to_history(message, "System")
            elif tag == "command":
                formatted_message = f"[{timestamp}] Command: {message}\n\n"
                self.add_to_history(message, "Command")
            else:
                formatted_message = f"[{timestamp}] {message}\n\n"
                
            self.ui.chat_display.insert("end", formatted_message, tag)
            self.ui.chat_display.see("end")
            self.ui.chat_display.config(state="disabled")
        except Exception as e:
            print(f"Error displaying message: {e}")
        
    def send_message(self, event=None):
        """Send a message from the input field"""
        try:
            message = self.ui.user_input.get().strip()
            if not message or self.is_typing:
                return
                
            if message in ["Type your question or /help...", "Type your question here..."]:
                return
                
            self.ui.user_input.delete(0, tk.END)
            self.display_message(message, "user")
            
            # Check if it's a slash command
            if message.startswith('/'):
                self.handle_slash_command(message)
            else:
                if self.ai_available:
                    threading.Thread(target=self.get_ai_response, args=(message,), daemon=True).start()
                else:
                    self.display_message("AI features not available. Try slash commands like /help", "system")
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def handle_slash_command(self, message):
        """Handle slash commands"""
        try:
            parts = message.split(' ', 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            
            if command in self.slash_commands:
                self.slash_commands[command](args)
            else:
                self.display_message(f"Unknown command: {command}. Type /help for available commands.", "system")
        except Exception as e:
            self.display_message(f"Error executing command: {str(e)}", "system")
    
    # Slash command implementations
    def show_help(self, args=""):
        """Show available slash commands"""
        help_text = """🤖 BroDev AI - Available Commands:

📁 FILE & SYSTEM:
/open_web <url> - Open URL in browser
/open_app <app> - Launch application
/open_folder [path] - Open folder
/search_files <pattern> - Search files
/create_file <name> - Create new file
/backup <src> <dest> - Backup files

ℹ️ INFORMATION:
/system_info - System information
/time - Current time
/calc <expression> - Calculator
/history - Chat history

📝 PRODUCTIVITY:
/note <text> - Save quick note
/todo <task> - Add to todo list
/screenshot - Take screenshot
/clear - Clear chat

💡 TIPS:
- Hover near right screen edge to show/hide
- Drag window to move it around
- Ask me anything for AI responses!"""
        
        self.display_message(help_text, "command")
    
    def open_web(self, args):
        """Open URL in browser"""
        if not args:
            self.display_message("Usage: /open_web <url>", "system")
            return
        
        url = args.strip()
        # Add https:// if not present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            webbrowser.open(url)
            self.display_message(f"✅ Opened: {url}", "command")
        except Exception as e:
            self.display_message(f"❌ Failed to open URL: {str(e)}", "system")
    
    def open_app(self, args):
        """Launch application"""
        if not args:
            self.display_message("Usage: /open_app <app_name>", "system")
            return
        
        app_name = args.strip()
        try:
            if platform.system() == "Windows":
                subprocess.Popen(app_name, shell=True)
            else:
                subprocess.Popen(app_name.split())
            self.display_message(f"🚀 Launched: {app_name}", "command")
        except Exception as e:
            self.display_message(f"❌ Failed to launch app: {str(e)}", "system")
    
    def open_folder(self, args):
        """Open folder in file manager"""
        folder_path = args.strip() if args else self.current_directory
        
        try:
            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.call(["open", folder_path])
            else:
                subprocess.call(["xdg-open", folder_path])
            self.display_message(f"📁 Opened folder: {folder_path}", "command")
        except Exception as e:
            self.display_message(f"❌ Failed to open folder: {str(e)}", "system")
    
    def search_files_command(self, args):
        """Search for files"""
        if not args:
            self.display_message("Usage: /search_files <pattern>", "system")
            return
        
        pattern = args.strip().lower()
        found_files = []
        search_dir = self.current_directory
        
        try:
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    if pattern in file.lower():
                        found_files.append(os.path.join(root, file))
                        if len(found_files) >= 20:  # Limit results
                            break
                if len(found_files) >= 20:
                    break
            
            if found_files:
                result = f"🔍 Found {len(found_files)} files matching '{pattern}':\n\n"
                for file in found_files:
                    result += f"• {file}\n"
            else:
                result = f"❌ No files found matching '{pattern}' in {search_dir}"
            
            self.display_message(result, "command")
        except Exception as e:
            self.display_message(f"❌ Search failed: {str(e)}", "system")
    
    def create_file_command(self, args):
        """Create a new file"""
        if not args:
            self.display_message("Usage: /create_file <filename>", "system")
            return
        
        filename = args.strip()
        try:
            # Create file in current directory
            filepath = os.path.join(self.current_directory, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# File created by BroDev AI\n# Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            self.display_message(f"✅ Created file: {filepath}", "command")
        except Exception as e:
            self.display_message(f"❌ Failed to create file: {str(e)}", "system")
    
    def system_info(self, args=""):
        """Show system information"""
        try:
            info = f"""💻 System Information:

🖥️ OS: {platform.system()} {platform.release()}
🏗️ Architecture: {platform.architecture()[0]}
🧠 Processor: {platform.processor() or 'Unknown'}
🐍 Python: {platform.python_version()}
📂 Current Directory: {self.current_directory}
🌐 Machine: {platform.machine()}
🏷️ Node: {platform.node()}"""
            
            self.display_message(info, "command")
        except Exception as e:
            self.display_message(f"❌ Failed to get system info: {str(e)}", "system")
    
    def clear_chat(self, args=""):
        """Clear chat history"""
        try:
            self.ui.chat_display.config(state="normal")
            self.ui.chat_display.delete(1.0, tk.END)
            self.ui.chat_display.config(state="disabled")
            self.display_message("🗑️ Chat cleared!", "system")
        except Exception as e:
            print(f"Error clearing chat: {e}")
    
    def show_time(self, args=""):
        """Show current time"""
        try:
            now = datetime.now()
            time_info = f"""⏰ Current Time Information:

📅 Date: {now.strftime('%Y-%m-%d')}
🕐 Time: {now.strftime('%H:%M:%S')}
📆 Day: {now.strftime('%A')}
📊 Week: {now.strftime('%U')} of {now.year}
🌍 Timezone: {time.tzname[0] if time.tzname else 'Unknown'}"""
            
            self.display_message(time_info, "command")
        except Exception as e:
            self.display_message(f"❌ Failed to get time: {str(e)}", "system")
    
    def get_weather(self, args):
        """Get weather information (placeholder)"""
        city = args.strip() if args else "your location"
        weather_msg = f"""🌤️ Weather Command

City: {city}
Status: Feature requires weather API integration

💡 To implement:
1. Get API key from OpenWeatherMap or similar
2. Install requests library
3. Make API call to get weather data

For now, check weather manually at:
https://weather.com or your preferred service"""
        
        self.display_message(weather_msg, "command")
    
    def calculate(self, args):
        """Calculate math expression"""
        if not args:
            self.display_message("Usage: /calc <expression>", "system")
            return
        
        try:
            expression = args.strip()
            # Safe evaluation - only allow basic math
            allowed_chars = set('0123456789+-*/.() ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                self.display_message(f"🧮 {expression} = {result}", "command")
            else:
                self.display_message("❌ Only basic math operations allowed (+, -, *, /, parentheses)", "system")
        except Exception as e:
            self.display_message(f"❌ Calculation error: {str(e)}", "system")
    
    def quick_note(self, args):
        """Save a quick note"""
        if not args:
            self.display_message("Usage: /note <text>", "system")
            return
        
        note_text = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {args}\n"
        try:
            notes_file = os.path.join(self.current_directory, "brodev_notes.txt")
            with open(notes_file, "a", encoding='utf-8') as f:
                f.write(note_text)
            self.display_message(f"📝 Note saved to {notes_file}:\n{args}", "command")
        except Exception as e:
            self.display_message(f"❌ Failed to save note: {str(e)}", "system")
    
    def todo_command(self, args):
        """Add to todo list"""
        if not args:
            self.display_message("Usage: /todo <task>", "system")
            return
        
        todo_item = f"[ ] {args} - Added: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        try:
            todo_file = os.path.join(self.current_directory, "brodev_todo.txt")
            with open(todo_file, "a", encoding='utf-8') as f:
                f.write(todo_item)
            self.display_message(f"✅ Added to todo list:\n{args}", "command")
        except Exception as e:
            self.display_message(f"❌ Failed to add todo: {str(e)}", "system")
    
    def take_screenshot(self, args=""):
        """Take a screenshot"""
        if not SCREENSHOT_AVAILABLE:
            self.display_message("❌ Screenshot feature requires 'pyautogui' library\nInstall with: pip install pyautogui", "system")
            return
            
        try:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = os.path.join(self.current_directory, filename)
            pyautogui.screenshot(filepath)
            self.display_message(f"📸 Screenshot saved: {filepath}", "command")
        except Exception as e:
            self.display_message(f"❌ Screenshot failed: {str(e)}", "system")
    
    def backup_files(self, args):
        """Backup files"""
        if not args:
            self.display_message("Usage: /backup <source> <destination>", "system")
            return
        
        parts = args.split(' ', 1)
        if len(parts) != 2:
            self.display_message("Usage: /backup <source> <destination>", "system")
            return
        
        source, dest = parts
        try:
            if os.path.isfile(source):
                shutil.copy2(source, dest)
                self.display_message(f"💾 File backed up: {source} → {dest}", "command")
            elif os.path.isdir(source):
                if os.path.exists(dest):
                    dest = os.path.join(dest, os.path.basename(source))
                shutil.copytree(source, dest, dirs_exist_ok=True)
                self.display_message(f"💾 Directory backed up: {source} → {dest}", "command")
            else:
                self.display_message(f"❌ Source not found: {source}", "system")
        except Exception as e:
            self.display_message(f"❌ Backup failed: {str(e)}", "system")
    
    def get_ai_response(self, message):
        """Get AI response from Groq"""
        if not self.ai_available:
            self.display_message("AI features not available. Check your Groq API key.", "system")
            return
            
        self.is_typing = True
        self.show_typing_indicator()
        
        try:
            system_prompt = """You are BroDev AI, a helpful programming and general assistant. 
            Provide clear, concise, and practical responses. When helping with code, 
            include explanations and best practices. Be friendly but professional.
            Keep responses under 500 words for better readability."""
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Recommended replacement
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.3,
                max_tokens=1024
            )
            ai_response = response.choices[0].message.content
        except Exception as e:
            ai_response = f"Sorry, I couldn't process your request: {str(e)}\nTry using slash commands instead!"
        
        self.root.after(0, self.display_ai_response, ai_response)
        
    def display_ai_response(self, response):
        """Display AI response in the chat"""
        self.hide_typing_indicator()
        self.display_message(response, "ai")
        self.is_typing = False
        
    def show_typing_indicator(self):
        """Show typing indicator animation"""
        try:
            self.ui.chat_display.config(state="normal")
            self.typing_pos = self.ui.chat_display.index("end-1c")
            self.ui.chat_display.insert("end", "🤖 BroDev AI is thinking...", "system")
            self.ui.chat_display.config(state="disabled")
            self.ui.chat_display.see("end")
            
            def animate():
                dots = 0
                while self.is_typing:
                    if self.typing_pos:
                        text = "🤖 BroDev AI is thinking" + "." * (dots % 4)
                        try:
                            self.ui.chat_display.config(state="normal")
                            current_end = self.ui.chat_display.index("end-1c")
                            self.ui.chat_display.delete(self.typing_pos, current_end)
                            self.ui.chat_display.insert(self.typing_pos, text, "system")
                            self.ui.chat_display.config(state="disabled")
                            self.ui.chat_display.see("end")
                        except tk.TclError:
                            break
                    dots += 1
                    time.sleep(0.5)
                    
            threading.Thread(target=animate, daemon=True).start()
        except Exception as e:
            pass
        
    def hide_typing_indicator(self):
        """Hide typing indicator"""
        try:
            if self.typing_pos:
                self.ui.chat_display.config(state="normal")
                current_end = self.ui.chat_display.index("end-1c")
                self.ui.chat_display.delete(self.typing_pos, current_end)
                self.ui.chat_display.config(state="disabled")
                self.typing_pos = None
        except:
            pass
    
    def close_app(self):
        """Close the application"""
        try:
            self.mouse_monitoring = False
            if hasattr(self, 'hover_zone') and self.hover_zone:
                self.hover_zone.destroy()
        except:
            pass
        self.root.quit()
        self.root.destroy()
        
    def start_move(self, event):
        """Start dragging the window"""
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        
    def on_move(self, event):
        """Move the window when dragging"""
        try:
            deltax = event.x - self._drag_data["x"]
            deltay = event.y - self._drag_data["y"]
            x = self.root.winfo_x() + deltax
            y = self.root.winfo_y() + deltay
            self.root.geometry(f"+{x}+{y}")
            
            # Update positions for hide/show functionality
            self.y = y
            self.hidden_x = self.screen_width - 10
            self.visible_x = self.screen_width - 450
        except Exception as e:
            pass
        
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.close_app()
        except Exception as e:
            print(f"Application error: {e}")
            self.close_app()


class UIComponents:
    def __init__(self, app):
        self.app = app
        
    def create_widgets(self):
        """Create all UI widgets"""
        try:
            self.main_frame = tk.Frame(self.app.root, bg="#1a1a1a")
            self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            self.main_frame.bind("<Enter>", self.app.on_mouse_enter)
            self.main_frame.bind("<Leave>", self.app.on_mouse_leave)
            
            self.create_header()
            self.create_input_area()
            self.create_chat_display()
            self.create_quick_action_buttons()
        except Exception as e:
            print(f"Error creating widgets: {e}")
        
    def create_header(self):
        """Create the header section"""
        try:
            header_frame = tk.Frame(self.main_frame, bg="#1a1a1a", height=50)
            header_frame.pack(fill="x", pady=(0, 10))
            header_frame.pack_propagate(False)
            
            header_frame.bind("<Enter>", self.app.on_mouse_enter)
            header_frame.bind("<Leave>", self.app.on_mouse_leave)
            
            # Close button
            close_btn = tk.Label(
                header_frame,
                text="✕",
                font=("Segoe UI", 14, "bold"),
                fg="#ff6b6b",
                bg="#1a1a1a",
                cursor="hand2"
            )
            close_btn.pack(side="right", pady=10)
            close_btn.bind("<Button-1>", lambda e: self.app.close_app())
            close_btn.bind("<Enter>", self.on_close_hover_enter)
            close_btn.bind("<Leave>", self.on_close_hover_leave)

            # Title
            title_label = tk.Label(
                header_frame,
                text="🤖 BroDev AI Assistant",
                font=("Segoe UI", 16, "bold"),
                fg="#87ceeb",
                bg="#1a1a1a"
            )
            title_label.pack(side="left", pady=10)
            title_label.bind("<Enter>", self.app.on_mouse_enter)
            title_label.bind("<Leave>", self.app.on_mouse_leave)
            
            # Status indicator
            status_text = "● Online" if self.app.ai_available else "● Limited"
            status_color = "#90EE90" if self.app.ai_available else "#FFB6C1"
            
            status_label = tk.Label(
                header_frame,
                text=status_text,
                font=("Segoe UI", 10),
                fg=status_color,
                bg="#1a1a1a"
            )
            status_label.pack(side="right", pady=10, padx=(0, 30))
            status_label.bind("<Enter>", self.app.on_mouse_enter)
            status_label.bind("<Leave>", self.app.on_mouse_leave)
            
            # Close button
            close_btn = tk.Label(
                header_frame,
                text="✕",
                font=("Segoe UI", 14, "bold"),
                fg="#ff6b6b",
                bg="#1a1a1a",
                cursor="hand2"
            )
            close_btn.pack(side="right", pady=10)
            close_btn.bind("<Button-1>", lambda e: self.app.close_app())
            close_btn.bind("<Enter>", self.on_close_hover_enter)
            close_btn.bind("<Leave>", self.on_close_hover_leave)
        except Exception as e:
            print(f"Error creating header: {e}")
        
    def on_close_hover_enter(self, event):
        """Handle close button hover"""
        event.widget.config(bg="#ff4444")
        self.app.on_mouse_enter()
        
    def on_close_hover_leave(self, event):
        """Handle close button hover leave"""
        event.widget.config(bg="#1a1a1a")
        
    def create_input_area(self):
        """Create the input area"""
        try:
            # Input label
            input_label = tk.Label(
                self.main_frame,
                text="💬 Ask me anything or use slash commands:",
                font=("Segoe UI", 11, "bold"),
                fg="white",
                bg="#1a1a1a"
            )
            input_label.pack(anchor="w", pady=(0, 5))
            input_label.bind("<Enter>", self.app.on_mouse_enter)
            input_label.bind("<Leave>", self.app.on_mouse_leave)
            
            # Input frame
            input_frame = tk.Frame(self.main_frame, bg="#1a1a1a")
            input_frame.pack(fill="x", pady=(0, 15))
            input_frame.bind("<Enter>", self.app.on_mouse_enter)
            input_frame.bind("<Leave>", self.app.on_mouse_leave)
            
            # Input entry
            self.user_input = tk.Entry(
                input_frame,
                font=("Segoe UI", 11),
                bg="#333333",
                fg="white",
                insertbackground="white",
                relief="flat",
                bd=5
            )
            self.user_input.pack(side="left", fill="x", expand=True, ipady=5)
            self.user_input.bind("<Return>", self.app.send_message)
            self.user_input.bind("<Enter>", self.app.on_mouse_enter)
            self.user_input.bind("<Leave>", self.app.on_mouse_leave)
            
            # Placeholder text handling
            self.user_input.insert(0, "Type your question or /help...")
            self.user_input.bind("<FocusIn>", self.clear_placeholder)
            self.user_input.bind("<FocusOut>", self.add_placeholder)
            self.user_input.config(fg="#888888")
            
            # Send button
            send_btn = tk.Button(
                input_frame,
                text="Send",
                font=("Segoe UI", 10, "bold"),
                bg="#87ceeb",
                fg="black",
                command=self.app.send_message,
                relief="flat",
                width=8,
                cursor="hand2"
            )
            send_btn.pack(side="right", padx=(5, 0), ipady=5)
            send_btn.bind("<Enter>", self.on_send_hover_enter)
            send_btn.bind("<Leave>", self.on_send_hover_leave)
        except Exception as e:
            print(f"Error creating input area: {e}")
            
    def on_send_hover_enter(self, event):
        """Handle send button hover"""
        event.widget.config(bg="#5f9ea0")
        self.app.on_mouse_enter()
        
    def on_send_hover_leave(self, event):
        """Handle send button hover leave"""
        event.widget.config(bg="#87ceeb")
        
    def clear_placeholder(self, event):
        """Clear placeholder text on focus"""
        if self.user_input.get() == "Type your question or /help...":
            self.user_input.delete(0, tk.END)
            self.user_input.config(fg="white")
            
    def add_placeholder(self, event):
        """Add placeholder text when empty"""
        if not self.user_input.get():
            self.user_input.insert(0, "Type your question or /help...")
            self.user_input.config(fg="#888888")
    
    def create_chat_display(self):
        """Create the chat display area"""
        try:
            # Chat label
            chat_label = tk.Label(
                self.main_frame,
                text="💭 Conversation:",
                font=("Segoe UI", 11, "bold"),
                fg="white",
                bg="#1a1a1a"
            )
            chat_label.pack(anchor="w", pady=(0, 5))
            chat_label.bind("<Enter>", self.app.on_mouse_enter)
            chat_label.bind("<Leave>", self.app.on_mouse_leave)
            
            # Chat frame with scrollbar
            chat_frame = tk.Frame(self.main_frame, bg="#1a1a1a")
            chat_frame.pack(fill="both", expand=True, pady=(0, 10))
            chat_frame.bind("<Enter>", self.app.on_mouse_enter)
            chat_frame.bind("<Leave>", self.app.on_mouse_leave)
            
            # Text widget for chat
            self.chat_display = tk.Text(
                chat_frame,
                font=("Segoe UI", 10),
                bg="#2a2a2a",
                fg="white",
                state="disabled",
                wrap="word",
                relief="flat",
                bd=5,
                padx=10,
                pady=10
            )
            self.chat_display.bind("<Enter>", self.app.on_mouse_enter)
            self.chat_display.bind("<Leave>", self.app.on_mouse_leave)
            
            # Scrollbar
            scrollbar = tk.Scrollbar(chat_frame, orient="vertical", command=self.chat_display.yview)
            self.chat_display.configure(yscrollcommand=scrollbar.set)
            
            self.chat_display.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Configure text tags for different message types
            self.chat_display.tag_configure("user", foreground="#87ceeb", font=("Segoe UI", 10, "bold"))
            self.chat_display.tag_configure("ai", foreground="#90EE90", font=("Segoe UI", 10))
            self.chat_display.tag_configure("system", foreground="#FFB6C1", font=("Segoe UI", 9))
            self.chat_display.tag_configure("command", foreground="#DDA0DD", font=("Segoe UI", 10))
            
            # Welcome message
            self.display_welcome_message()
        except Exception as e:
            print(f"Error creating chat display: {e}")
    
    def display_welcome_message(self):
        """Display welcome message"""
        try:
            self.chat_display.config(state="normal")
            welcome_msg = f"""🚀 Welcome to BroDev AI Assistant!

✨ Features:
• AI-powered conversations ({"✅ Ready" if self.app.ai_available else "❌ Setup needed"})
• File management commands
• System utilities
• Productivity tools

🎯 Quick Start:
• Type /help to see all commands
• Ask me anything for AI responses
• Hover near screen edge to show/hide
• Drag the window to move it

💡 Popular Commands:
/open_web google.com
/system_info
/time
/clear

Ready to assist! 🤖
"""
            
            self.chat_display.insert("end", welcome_msg, "system")
            self.chat_display.config(state="disabled")
        except Exception as e:
            print(f"Error displaying welcome message: {e}")

    def create_quick_action_buttons(self):
        """Create quick action buttons"""
        try:
            # Container frame
            quick_actions_container = tk.Frame(self.main_frame, bg="#1a1a1a")
            quick_actions_container.pack(fill="x", pady=(5, 0))
            
            # Label
            quick_actions_label = tk.Label(
                quick_actions_container,
                text="⚡ Quick Actions:",
                font=("Segoe UI", 10, "bold"),
                fg="white",
                bg="#1a1a1a"
            )
            quick_actions_label.pack(pady=(0, 8))
            quick_actions_label.bind("<Enter>", self.app.on_mouse_enter)
            quick_actions_label.bind("<Leave>", self.app.on_mouse_leave)
            
            # Button rows
            button_row1 = tk.Frame(quick_actions_container, bg="#1a1a1a")
            button_row1.pack(pady=2)
            
            button_row2 = tk.Frame(quick_actions_container, bg="#1a1a1a")
            button_row2.pack(pady=2)
            
            # Button configuration
            btn_config = {
                "font": ("Segoe UI", 8, "bold"),
                "relief": "flat",
                "width": 9,
                "height": 1,
                "cursor": "hand2",
                "bd": 2
            }
            
            # First row buttons
            buttons_row1 = [
                ("🗑️ Clear", "#ff6b6b", "white", lambda: self.app.slash_commands["/clear"]("")),
                ("❓ Help", "#32CD32", "white", lambda: self.app.slash_commands["/help"]("")),
                ("🌐 Web", "#87ceeb", "black", lambda: self.insert_command("/open_web ")),
                ("📜 History", "#DDA0DD", "black", lambda: self.app.slash_commands["/history"](""))
            ]
            
            for text, bg, fg, cmd in buttons_row1:
                btn = tk.Button(button_row1, text=text, bg=bg, fg=fg, command=cmd, **btn_config)
                btn.pack(side="left", padx=2)
                btn.bind("<Enter>", lambda e, b=btn: self.on_button_hover_enter(e, b))
                btn.bind("<Leave>", lambda e, b=btn, orig_bg=bg: self.on_button_hover_leave(e, b, orig_bg))
            
            # Second row buttons
            buttons_row2 = [
                ("ℹ️ Info", "#9370DB", "white", lambda: self.app.slash_commands["/system_info"]("")),
                ("⏰ Time", "#FF69B4", "white", lambda: self.app.slash_commands["/time"]("")),
                ("📁 Folder", "#FF8C00", "white", lambda: self.app.slash_commands["/open_folder"]("")),
                ("🧮 Calc", "#20B2AA", "white", lambda: self.insert_command("/calc "))
            ]
            
            for text, bg, fg, cmd in buttons_row2:
                btn = tk.Button(button_row2, text=text, bg=bg, fg=fg, command=cmd, **btn_config)
                btn.pack(side="left", padx=2)
                btn.bind("<Enter>", lambda e, b=btn: self.on_button_hover_enter(e, b))
                btn.bind("<Leave>", lambda e, b=btn, orig_bg=bg: self.on_button_hover_leave(e, b, orig_bg))
                
        except Exception as e:
            print(f"Error creating quick action buttons: {e}")
    
    def on_button_hover_enter(self, event, button):
        """Handle button hover enter"""
        current_bg = button.cget("bg")
        # Darken the color slightly
        if current_bg == "#ff6b6b":
            button.config(bg="#e55555")
        elif current_bg == "#32CD32":
            button.config(bg="#28a428")
        elif current_bg == "#87ceeb":
            button.config(bg="#6bb6d6")
        elif current_bg == "#DDA0DD":
            button.config(bg="#c285c2")
        elif current_bg == "#9370DB":
            button.config(bg="#7a5bc7")
        elif current_bg == "#FF69B4":
            button.config(bg="#e553a0")
        elif current_bg == "#FF8C00":
            button.config(bg="#e67e00")
        elif current_bg == "#20B2AA":
            button.config(bg="#1a9e96")
        self.app.on_mouse_enter()
    
    def on_button_hover_leave(self, event, button, original_bg):
        """Handle button hover leave"""
        button.config(bg=original_bg)

    def insert_command(self, command):
        """Insert a slash command into the input field"""
        try:
            self.user_input.delete(0, tk.END)
            self.user_input.insert(0, command)
            self.user_input.config(fg="white")
            self.user_input.focus()
        except Exception as e:
            print(f"Error inserting command: {e}")


if __name__ == "__main__":
    print("🚀 Starting BroDev AI Assistant...")

    
    try:
        app = BroDevAI()
        app.run()
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        print("Please check your Python installation and try again.")