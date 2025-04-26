import weaviate
from weaviate.classes.config import Configure
import inspect

# Print the signature of the Configure.sharding method
print("Configure.sharding signature:")
print(inspect.signature(Configure.sharding))

# Print the docstring of the Configure.sharding method
print("\nConfigure.sharding docstring:")
print(Configure.sharding.__doc__)