class Py3status:
    text = " ✨ Hello from py3status — stay hydrated ✨   "
    step = 1
    interval = 0.2
    color = "#bfbaac"
    index = 0

    def scrolling_text(self):
        if not self.text:
            return {"full_text": "", "cached_until": self.py3.time_in(2)}
        self.index = (self.index + self.step) % len(self.text)
        rotated = self.text[self.index:] + self.text[:self.index]
        return {
            "full_text": f"<span foreground='{self.color}'>{rotated}</span>",
            "cached_until": self.py3.time_in(self.interval)
        }

