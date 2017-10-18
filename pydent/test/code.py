from time import gmtime, strftime
from pydent import *

Session.create_from_config_file("secrets/config.json")

# Get and change an operation type's cost model
pcr = aq.OperationType.find_by_name("Make PCR Fragment")
code = pcr.code("cost_model") # can also do "protocol", "documentation", etc.
print(code.content)

code.content = "# Kilroy was here " +\
             strftime("%Y-%m-%d %H:%M:%S", gmtime()) +\
             "\n" +\
             code.content

code.update()
print(code.content)

# Get and change a library's code
lib = aq.Library.find_by_name("MyLib")
code = lib.code("source")
print(code.content)

code.content = "# Kilroy was here " +\
             strftime("%Y-%m-%d %H:%M:%S", gmtime()) +\
             "\n" +\
             code.content

code.update()
print(code.content)