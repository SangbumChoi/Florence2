import torch
import torch.nn as nn
from florence2.models.backbone.davit import DaViT_base, DaViT_large_window12_384
from florence2.models.head.bart import Bart
from florence2.models.projection.linear import LinearProjection


class Florence2(nn.Module):
    r"""Florence 2 model

    Args:
        config (dict) :
            backbone (dict):
                type (str) : backbone_type for DaViT. Default: base
                weight (str): pretrained weight path for backbone model. Default: None
                return_feature (bool): exclude classification head for backbone. Default: True
    """

    def __init__(
        self,
        config: dict,
    ):
        super().__init__()

        backbone_type = config["backbone"]["type"]
        backbone_weight = config["backbone"]["weight"]
        backbone_return_feature = config["backbone"]["return_feature"]

        if backbone_type == "base":
            self.image_encoder = DaViT_base(
                pretrained=backbone_weight, return_feature=backbone_return_feature
            )
        elif backbone_type == "large":
            self.image_encoder = DaViT_large_window12_384(
                pretrained=backbone_weight, return_feature=backbone_return_feature
            )
        else:
            assert False, f"backbone_name is {backbone_type} which is not defined"

        self.visual_projection = LinearProjection(
            in_features=1024, hidden_features=1024
        )

        self.bart = Bart(model_name="facebook/bart-large")

    def encode_image(self, image):
        image_feature = self.image_encoder(image)
        return image_feature

    def encode_text(self, text):
        token = self.bart.encode(text=text)
        text_token = token["input_ids"]
        text_feature = self.bart.extract_embedding(tokens=text_token)
        return text_feature, text_token

    def forward(self, image, text):
        image_features = self.encode_image(image)
        text_features, text_token = self.encode_text(text)

        # single step visual projection
        image_features = self.visual_projection(image_features)

        concat_features = torch.cat([image_features, text_features], dim=1)

        output = self.bart(inputs_embeds=concat_features, decoder_input_ids=text_token)
        return output


if __name__ == "__main__":
    config = {"backbone": {"type": "base", "weight": False, "return_feature": True}}
    florence_model = Florence2(config=config)
    x = torch.rand([1, 3, 224, 224])
    text = ["This is the test text"]
    y = florence_model(x, text)
    print("input", x.shape)
    print("output", y)
