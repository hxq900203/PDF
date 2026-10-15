from dataclasses import dataclass

DPI_CHOICES = (150, 200, 300)


@dataclass
class Options:
    dpi: int = 200
    merge_images: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Options":
        dpi = d.get("dpi", 200)
        if dpi not in DPI_CHOICES:
            dpi = 200
        return cls(dpi=dpi, merge_images=bool(d.get("merge_images", False)))
