# LLM Dixit arena

Have different LLM play Dixit among them. To be used as a true benchmark of their ``reasoning'' capabilities

# Data

### overviews
in data/overviews you can get the *original* dixit card overviews as downloaded from https://www.libellud.com/en/resources/dixit/

## other cards
https://uk.pinterest.com/cassagram/dixit-cards/

# Resources

https://dl.acm.org/doi/abs/10.1145/3555858.3555863
https://github.com/hav4ik/dixit-chatgpt
https://arxiv.org/pdf/2010.00048
https://arxiv.org/abs/2206.08349

interaction data http://www.spronck.net/datasets/Dixit_AI_data.zip

# Run tests
pytest --env=.env  
export PYTHONPATH=src
pytest
