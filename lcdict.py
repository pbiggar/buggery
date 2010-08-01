
class arbitrary_dict(dict):
  """A dictionary which applies an arbitrary key-altering function before accessing the keys"""

  def __keytransform__(self, key):
    return key

  # Overrided methods. List from a http://stackoverflow.com/questions/2390827/how-to-properly-subclass-dict
  def __init__(self, *args, **kwargs):
    self.update(*args, **kwargs)

  # Use dict directly, since super(dict, self) doesn't work. Not sure why, perhaps dict is not a new-style class.
  def __getitem__(self, key):
    return dict.__getitem__(self, self.__keytransform__(key))

  def __setitem__(self, key, value):
    return dict.__setitem__(self, self.__keytransform__(key), value)

  def __delitem__(self, key):
    return dict.__delitem__(self, self.__keytransform__(key))

  def __contains__(self, key):
    return dict.__contains__(self, self.__keytransform__(key))



class lcdict(arbitrary_dict):

  def __keytransform__(self, key):
    return str(key).lower()




def test_simple():
  x = lcdict()
  # check can access with a different case permutation
  x["AsD"] = 5
  assert x["aSd"] == 5

  # check setting sets the same key
  x["ASd"] = 6
  assert len(x) == 1


  # check we didn't break keys entirely
  x["abc"] = 7
  assert len(x) == 2

  # check the get() function
  assert x.get("ABC") == 7
