import re
import json
import os
import time

class PlayerManager:
    def __init__(self, server_path: str = None):
        self.server_path = server_path
        self.players = {} # {username: {"rank": "User", "ping": "?", "discord": "", "balance": ""}}
        
        # ANSI Escape Codes Regex
        self.re_ansi = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        
        # Regex Patterns (Enhanced)
        # Matches: [12:00:00 INFO]: Steve joined the game
        # Matches: [12:00:00 INFO]: [Admin] Steve joined the game (if chat plugin modifies it)
        # Note: We look for " joined the game" and take what's before it, splitting by space.
        
        # Standard Vanilla/Paper
        self.re_join = re.compile(r": ([\w_]+) joined the game") 
        self.re_leave = re.compile(r": ([\w_]+) left the game")
        
        self.re_uuid = re.compile(r"UUID of player (.*?) is (.*)")
        self.re_op = re.compile(r": Made (.*?) a server operator")
        self.re_deop = re.compile(r": Made (.*?) no longer a server operator")
        
        # List Command Response (Vanilla/Paper)
        # "There are 1 of 20 players online: Steve"
        # "There are 2 of 20 players online: Steve, Alex"
        self.re_list_header = re.compile(r"There are (\d+) of (\d+) players online:")

    def strip_ansi(self, text: str) -> str:
        return self.re_ansi.sub('', text)

    def parse_log(self, line: str) -> bool:
        """Parses a log line and updates player list. Returns True if list changed."""
        clean_line = self.strip_ansi(line)
        changed = False
        
        # 1. Join
        match_join = self.re_join.search(clean_line)
        if match_join:
            player = match_join.group(1).strip()
            if player and player not in self.players:
                self.players[player] = {"rank": "User", "ping": "?"}
                changed = True  # Only change if new
                
        # 2. Leave
        match_leave = self.re_leave.search(clean_line)
        if match_leave:
            player = match_leave.group(1).strip()
            if player in self.players:
                del self.players[player]
                changed = True

        # 3. OP Status
        match_op = self.re_op.search(clean_line)
        if match_op:
            player = match_op.group(1).strip()
            if player in self.players:
                self.players[player]["rank"] = "OP"
                changed = True
        
        match_deop = self.re_deop.search(clean_line)
        if match_deop:
            player = match_deop.group(1).strip()
            if player in self.players:
                self.players[player]["rank"] = "User"
                changed = True

        # 4. List Command (Sync)
        # Output is usually two lines? Or one?
        # "There are 1 of 20 players online: Steve, Alex" -> single line usually
        if "players online:" in clean_line:
            match_list = self.re_list_header.search(clean_line)
            if match_list:
                # Extract part after "online:"
                try:
                    parts = clean_line.split("online:", 1)
                    if len(parts) > 1:
                        names_str = parts[1].strip()
                        if not names_str: # No users
                            if self.players: # If we had users, clear them
                                self.players = {}
                                changed = True
                        else:
                            # Split by comma
                            current_online = [n.strip() for n in names_str.split(",")]
                            
                            # Sync Logic:
                            # 1. Add missing
                            for p in current_online:
                                if p and p not in self.players:
                                    self.players[p] = {"rank": "User", "ping": "?"}
                                    changed = True
                            
                            # 2. Remove ghosts
                            ghosts = [p for p in self.players if p not in current_online]
                            for g in ghosts:
                                del self.players[g]
                                changed = True
                except:
                    pass

        return changed

    def sync_with_json(self) -> dict:
        """Reads server-state.json if available and updates players. Returns server stats (tps, ram) or None."""
        if not self.server_path:
            return None
            
        json_path = os.path.join(self.server_path, "server-state.json")
        if not os.path.exists(json_path):
            return None
            
        try:
            # Check modification time to avoid re-reading if not needed? 
            # For now, just read. It's small.
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # data schema: { "tps": 20.0, "rams_used": ..., "players": [...] }
            json_players = data.get("players", [])
            
            # Use JSON as the source of truth for the list if available
            # But we might want to keep local formatting if log parsed something faster?
            # Actually JSON is more reliable for metadata.
            
            current_names = set()
            
            for p in json_players:
                name = p.get("name")
                if not name: continue
                
                current_names.add(name)
                
                if name not in self.players:
                    self.players[name] = {}
                    
                # Update/Merge info
                self.players[name]["uuid"] = p.get("uuid", "")
                self.players[name]["ping"] = str(p.get("ping", "?")) + "ms"
                
                # Balance formatting
                bal = p.get("balance", 0)
                self.players[name]["balance"] = f"${bal:,.0f}"
                
                # Discord
                d_tag = p.get("discordTag", "")
                d_id = p.get("discordId", "")
                if d_tag and d_tag != "null":
                    self.players[name]["discord"] = d_tag
                else:
                    self.players[name]["discord"] = "No Link"
                    
                # Rank (Logic: logs might give OP, but JSON might give Permissions groups later)
                # Keep existing rank if set by log (OP), else default
                if "rank" not in self.players[name]:
                    self.players[name]["rank"] = "User"
            
            # Remove ghosts (players in memory but not in JSON? 
            # Careful: JSON might lag behind logs. 
            # Strategy: If JSON is recent (< 5s old), trust it for removal.)
            mtime = os.path.getmtime(json_path)
            if time.time() - mtime < 5:
                # Trust JSON for removals
                toremove = [n for n in self.players if n not in current_names]
                for n in toremove:
                    del self.players[n]
            
            return {
                "tps": data.get("tps", 20.0),
                "ram_used": data.get("rams_used", 0),
                "ram_max": data.get("rams_max", 0)
            }
            
        except Exception as e:
            # print(f"Error reading JSON: {e}") 
            return None

    def get_players(self):
        return self.players
        
    def clear(self):
        self.players = {}
