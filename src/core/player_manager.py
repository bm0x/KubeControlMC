import re

class PlayerManager:
    def __init__(self):
        self.players = {} # {username: {"rank": "User", "ping": "?"}}
        
        # Regex Patterns (Paper/Spigot standard)
        self.re_join = re.compile(r": (.*?) joined the game")
        self.re_leave = re.compile(r": (.*?) left the game")
        self.re_uuid = re.compile(r"UUID of player (.*?) is (.*)")
        self.re_op = re.compile(r": Made (.*?) a server operator")
        self.re_deop = re.compile(r": Made (.*?) no longer a server operator")

    def parse_log(self, line: str) -> bool:
        """Parses a log line and updates player list. Returns True if list changed."""
        changed = False
        
        # Clean line (remove timestamp and thread info roughly if needed, 
        # but regex usually handles the mismatch with greedy match)
        
        # Join
        match_join = self.re_join.search(line)
        if match_join:
            player = match_join.group(1)
            if player not in self.players:
                self.players[player] = {"rank": "User", "ping": "?"}
                changed = True
                
        # Leave
        match_leave = self.re_leave.search(line)
        if match_leave:
            player = match_leave.group(1)
            if player in self.players:
                del self.players[player]
                changed = True

        # OP / DEOP
        match_op = self.re_op.search(line)
        if match_op:
            player = match_op.group(1)
            # Update rank even if offline, or just if online. 
            # Ideally luckperms would handle this, but for vanilla OP:
            if player in self.players:
                self.players[player]["rank"] = "OP"
                changed = True

        match_deop = self.re_deop.search(line)
        if match_deop:
            player = match_deop.group(1)
            if player in self.players:
                self.players[player]["rank"] = "User"
                changed = True

        return changed

    def get_players(self):
        return self.players
        
    def clear(self):
        self.players = {}
