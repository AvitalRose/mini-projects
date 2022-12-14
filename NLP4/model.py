import torch.nn as nn
import torch
from utils import SentenceEncoder


class DistanceBasedModel(nn.Module):
    def __init__(self, args, embedding_dict):
        super().__init__()
        self.device = args.device
        self.dropout_rate = args.dropout
        self.embedding_dim = args.embedding_dim
        self.relu_layer_dim = args.relu_layer_dim
        self.targets_size = args.targets_size
        linear_layer_input_size = args.embedding_dim * 4 * 4

        self.embedding = nn.Embedding(len(embedding_dict), len(embedding_dict[0]))
        self.embedding.weight.data.copy_(torch.from_numpy(embedding_dict))  # getting weights from
        self.embedding.weight.requires_grad = False  # don't want to train the weights for the embedding
        nn.init.uniform_(self.embedding.weight.data[1], -0.05, 0.05)  # initialize the unknown embedding uniformly

        self.sentence_encoder = SentenceEncoder(args)
        self.linear1 = nn.Linear(linear_layer_input_size, self.relu_layer_dim)
        self.linear2 = nn.Linear(self.relu_layer_dim, self.targets_size)
        self.relu = nn.ReLU()
        self.softmax = nn.Softmax(dim=1)

        self.dropout = nn.Dropout(self.dropout_rate)
        self.layer_norm = nn.LayerNorm(self.embedding_dim)

    def forward(self, inputs):
        """
        First, the two input sentences, premise and hypothesis, are encoded as vectors, u and v respectively, through
        identical sentence encoders. For the encoded vectors u and v, the representation of relation between the two
        vectors is generated by the concatenation of u, v, |u − v|, and u ∗ v.
        Thereafter, a probability for each of the 3-class is generated through the 300D ReLU layer and the 3-way
        softmax output layer. Layer normalization and dropout are applied to 300D ReLU layer.
        :param inputs: list of tensors
        :return:
        """
        premise, premise_lengths, hypothesis, hypothesis_lengths = inputs

        # encoding sentences
        # development, chop batch to smaller size
        premise = premise[:, :max(premise_lengths)]
        hypothesis = hypothesis[:, :max(hypothesis_lengths)]

        premise = premise.to(self.device)
        hypothesis = hypothesis.to(self.device)

        # embedding layer
        premise_embedding = self.embedding(premise)
        hypothesis_embedding = self.embedding(hypothesis)

        # sentence encoder
        encoded_premise = self.sentence_encoder(premise_embedding, premise_lengths)
        encoded_hypothesis = self.sentence_encoder(hypothesis_embedding, hypothesis_lengths)

        # representation - concatenate u, v, |u − v|, and u ∗ v
        abs_pre_hyp = (encoded_premise - encoded_hypothesis).abs()
        mul_pre_hyp = encoded_premise * encoded_hypothesis
        concatenated_representation = torch.cat([encoded_premise, encoded_hypothesis, abs_pre_hyp, mul_pre_hyp], dim=-1)

        concatenated_representation = self.dropout(concatenated_representation)
        output = self.linear1(concatenated_representation)
        output = self.layer_norm(output)
        output = self.relu(output)

        output = self.dropout(output)
        output = self.linear2(output)
        output = self.softmax(output)

        return output


if __name__ == "__main__":
    pass
