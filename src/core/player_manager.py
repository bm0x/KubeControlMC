import re

class PlayerManager:
    def __init__(self):
        self.players = {} # {username: {"rank": "User", "ping": "?"}}
        
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

    def get_players(self):
        return self.players
        
    def clear(self):
        self.players = {}
