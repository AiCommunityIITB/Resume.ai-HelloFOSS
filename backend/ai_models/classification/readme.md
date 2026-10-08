Classification Model 
---

Problem statement : Create a BERT based model to take input text as projects and statements about work done by a person and classify them into predefined classes.

Research and model choosing
---
For the basic model we used in the AIC assignment was the vanilla version of BERT model. For this I research some famous and much more accurate models and the following are my findings. The simple model used by us was BERT with 12 transformer encoding layers, and 110 million parameters. It is pretrained on the objective of MLM and NSP and trains using bidriectional context viewing. 
The other models we can consider instead of the BERT base uncased model are :
-
1. RoBERTa Base : It has 2-3% more accuracy and it is trained on way more data. It also uses Dynamic masking, i.e. chooses different values to mask for each batch and it has more batches too.

2. DeBERTa v3 base : This has the state-of-the-art accuracy and better at long context handling, however for our use case, i think the maximum context handling would be needed for not more than 100-200 words becuase each block of text would contain related text to one project or topic so context handling might not be needed. However, its still a good upgrade. One of the best benefits is, it doesn't need a lot of data for training, we have around 400 resumes so that is a good amount of data that can be used to train a deberta base model. 

3. ELECTRA base : It has better accuracy than the BERT base model but it has been trained on less data, hence less robust. Its main training objective is replaced token detection objective, might not be the best choice for our use case.
-

I read upon many more models but the most ideal model is DeBERTA v3 base model, one more reason for choosing this was I have a RTX3050 4GB VRAM, so this was the best model for my GPU with the max accuracy. It also uses a disentangled attention mechanism and an advanced pretraining approach for better handling of document structure and context.

Model stats and Mechanism
---

Model Architecture and Key Stats:\
Layers: 12 Transformer encoder layers\
Hidden Size: 768\
Total Parameters:\
Backbone: 86 million\
Embedding: 98 million\
Total: ~184 million parameters\
Vocabulary Size: 128,000 tokens\
Training Data Used: 160GB of text\
Max Sequence Length: 512 tokens\