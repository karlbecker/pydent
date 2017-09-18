import sys
sys.path.append('.')

import aq

aq.login()

# Test getting an item and showing all of its associations

i = aq.Item.find(1111)

print("Item " + str(i.id) + " is located at " + i.location)
print(i.object_type.name)
print(i.sample.sample_type.name)
print(i.sample.name)

das = i.data_associations
print([[da.key,da.value] for da in das])
print([da.upload.temp_url if da.upload else "-" for da in das])

# Test getting an item with some associations already included

i = aq.Item.where(
  {"id": 1111},
  { "include": "object_type",
    "methods": ["data_associations"]
  }
)[0]

print(i.object_type.name)
das = i.data_associations
print([[da.key,da.value] for da in das])