from pprint import pprint
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker.scrappers.darkerprojects import DarkerProjects
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

print("=== AudioAnarchy (first 2) ===")
for i, book in enumerate(AudioAnarchy().iterate_all()):
    pprint(book.title)
    if i >= 1:
        break

print("=== DarkerProjects (first 2) ===")
for i, book in enumerate(DarkerProjects().iterate_all()):
    pprint(book.title)
    if i >= 1:
        break

print("=== GoldenAudioBooks (first 2) ===")
for i, book in enumerate(GoldenAudioBooks().iterate_all()):
    pprint(book.title)
    if i >= 1:
        break

print("=== HPTalesAudioBooks (first 2) ===")
for i, book in enumerate(HPTalesAudioBooks().iterate_all()):
    pprint(book.title)
    if i >= 1:
        break

print("=== StephenKingAudioBooks search ===")
for book in StephenKingAudioBooks().search("Dark Tower"):
    pprint(book.title)
    break
