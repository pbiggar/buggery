class UserError(Exception):
  def __init__(self, message, parseobj):
    self.message = message
    self.parseobj = parseobj

  def line_number(self):
    return getattr(self.parseobj, 'lineno', '??')

  def column_number(self):
    return getattr(self.parseobj, 'colno', '??')

class CommandError(Exception):
  def __init__(self, proc):
    self.proc = proc
