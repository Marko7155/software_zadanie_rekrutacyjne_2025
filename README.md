# Zadanie rekrutacyjne, AGH Space Systems Rocket Software jesień 2025

Oto moja wersja zadania rekrutacyjnego -> zautomatyzowanie symulatora lotu rakiety od uzupełnienia utleniacza po lądowanie.
Program otrzymuje ramki od symulowanej rakiety i podejmuje odpowiednie akcje, tak aby uniknąć awarii i prawidłowo przeprowadzić lot rakiety.

Moje zmiany są zamknięte w dwóch plikach:
- ```software_simulation_structure.py``` - znajdują się w nim utworzone klasy w celu abstrakcji powtarzających się części kodu i poprawienia ogólnej czytelności,

- ```software_simulation.py``` - właściwa część symulatora, rejestruje callbacki i wykonuje operacje w wymaganej kolejności.

## Dlaczego wybrałem takie zadanie?

Uważam, że komunikacja pomiędzy dwoma urządzeniami na odległość jest trudnym, ale niezwykle ważnym zagadnieniem. Niegdy przedtem nie wchodziłem z interakcje z innym systemem na "odległość" (oprócz komunikacji HTTP, ale jest to całkowicie co innego) w jego własnym protokole komunikacyjnym. To zadanie było naprawdę ciekawe i bardzo przyjemnie się go robiło.

## Możliwości rozwoju/poprawek

- Mimo wstępnej dekompozycji duża część kodu się powtarza - jest to głównie tworzenie ramek. Nie wiem jak to powinno wyglądać, dlatego zostawiłem tak jak jest. Gdybym miał jednak wrócić do tego kodu, to spróbowałbym zrobić coś w stylu ```frame_factory``` lub przerzuciłbym je do osobnego pliku,

- Kod da się również lepiej porozdzielać (szczególnie klasę ```Ignition``` by mogła poprawnie korzystać z dziedziczenia), dzięki czemu możnaby uzyskać większą przejrzystość/strukturę,

- Dodać GUI, na które niestety nie starczyło mi czasu, co poprawiłoby czytelność i interpretację danych spływających z sensorów i serwomechanizmów.