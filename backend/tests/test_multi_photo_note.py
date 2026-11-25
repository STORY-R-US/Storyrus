"""Várias fotos originais: instrução para o modelo de imagem."""

from app.services import book_profile


def test_single_photo_still_forbids_duplicate_people():
    assert book_profile.multi_photo_note([b"one"]) == book_profile.NO_DUPLICATE_PEOPLE
    assert book_profile.multi_photo_note([]) == book_profile.NO_DUPLICATE_PEOPLE
    assert "exactly once" in book_profile.NO_DUPLICATE_PEOPLE


def test_several_photos_are_combined_as_one_person_without_duplicates():
    note = book_profile.multi_photo_note([b"one", b"two", b"three"])

    assert "the 3 original identity photographs" in note
    assert "ONE individual" in note
    assert "exactly once" in note
    assert "never create twins" in note
    assert "NO DUPLICATE PEOPLE" in note
