class UserError(Exception):
  def __init__(self, msg, parseobj):
    self.msg = msg
    self.parseobj = parseobj

  def line_number(self):
    return getattr(self.parseobj, 'lineno', '??')

  def column_number(self):
    return getattr(self.parseobj, 'colno', '??')

class CommandError(Exception):
  def __init__(self, proc):
    self.proc = proc
