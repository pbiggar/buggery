class UserError(Exception):
  def __init__(self, message):
    self.message = message

class CommandError(Exception):
  def __init__(self, proc):
    self.proc = proc
