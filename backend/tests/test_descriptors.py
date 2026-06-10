import numpy as np
import pytest

from app.qsar.descriptors import DescriptorEngine


def test_descriptor_engine_extracts_expected_counts():
    result = DescriptorEngine().build("CCO", solvent_eps=24.3, solvent_ri=1.36)

    assert result.atom_count == 3
    assert result.carbon_count == 2
    assert result.hetero_count == 1
    assert result.vector.shape == (13,)
    assert np.isfinite(result.vector).all()


def test_descriptor_engine_rejects_untokenizable_structure():
    with pytest.raises(ValueError, match="cannot be tokenized"):
        DescriptorEngine().build("[]", solvent_eps=24.3, solvent_ri=1.36)
