from dataclasses import asdict, dataclass, field
import typing
import json
import sys

import reverse_geocoder
import geocoder

from src.full_random import FullRandom 


@dataclass
class Place():
    name: str
    lat: typing.Union[None, float]
    lon: typing.Union[None, float]

DEFAULT_PLACE_COUNT = 200

@dataclass
class Region():
    search_string: str
    requested_place_count: int = DEFAULT_PLACE_COUNT
    actual_place_count: typing.Union[None, int] = None
    resolved_name: typing.Union[None, str] = None
    bb_lat_1: typing.Union[None, float] = None
    bb_lat_2: typing.Union[None, float] = None
    bb_lon_1: typing.Union[None, float] = None
    bb_lon_2: typing.Union[None, float] = None
    places: typing.List[Place] = field(default_factory=list)


MATCH_ON = 'admin1'

MATCH_FAIL_LIMIT = DEFAULT_PLACE_COUNT * 5

REGIONS = [
    Region("Australian Capital Territory, Australia", requested_place_count=6),
    Region("New South Wales, Australia"),
    Region("Northern Territory, Australia", requested_place_count=10),
    Region("Queensland, Australia", requested_place_count=90),
    Region("South Australia, Australia", requested_place_count=80),
    Region("Tasmania, Australia", requested_place_count=35),
    Region("Victoria, Australia", requested_place_count=150),
    Region("Western Australia, Australia", requested_place_count=80)
]

def run():
    print("Resolving and finding bounding boxes for regions")

    for region in REGIONS:
        print(f"Searching for '{region.search_string}'")
        g = geocoder.arcgis(region.search_string)
        region.resolved_name = g.geojson['features'][0]['properties']['address']
        region.bb_lat_1 = g.geojson['features'][0]['properties']['bbox'][1]
        region.bb_lat_2 = g.geojson['features'][0]['properties']['bbox'][3]
        region.bb_lon_1 = g.geojson['features'][0]['properties']['bbox'][0]
        region.bb_lon_2 = g.geojson['features'][0]['properties']['bbox'][2]

    print("Generating places")
    fr = FullRandom()
    for region in REGIONS:
        print(f"Generating places for '{region.search_string}'")
        failed_with_results = False

        for i in range(region.requested_place_count):
            searching = True
            fail_count = 0

            while searching:
                rnd_lat = fr.uniform(region.bb_lat_1, region.bb_lat_2)
                rnd_lon = fr.uniform(region.bb_lon_1, region.bb_lon_2)
                res = reverse_geocoder.search((rnd_lat, rnd_lon))

                if len(res) == 0:
                    continue

                record = res[0]
                if record[MATCH_ON] == region.resolved_name:
                    if record['name'] in [p.name for p in region.places]:
                        # print(f'Duplicate place for {region.resolved_name} ({record["name"]}) detected, retrying...')
                        fail_count += 1
                    else:
                        region.places.append(Place(record['name'], record['lat'], record['lon']))
                        searching = False
                        break
                
                fail_count += 1

                if fail_count >= MATCH_FAIL_LIMIT:
                    if len(region.places) == 0:
                        print(f'Unable to match region {region.resolved_name} against geocoded locations after {MATCH_FAIL_LIMIT} attempts.')
                        print(f'{len(region.place)} places were found.')
                        print(f'Check search queries, or MATCH_ON ("{MATCH_ON}") or increase MATCH_FAIL_LIMIT and try again')
                        sys.exit(1)
                    
                    print(f'Hit fail limit for {region.resolved_name}')
                    print(f'{region.requested_place_count} places were requested but only {len(region.places)} could be generated.')
                    failed_with_results = True
                    searching = False

            if failed_with_results:
                # stop processing on i
                break


    print("Merging results")
    memo = { "data": [] }
    for region in REGIONS:
        region.actual_place_count = len(region.places)
        memo["data"].append(asdict(region))
    print("Writing result.json")
    with open("results.json", 'wt') as fp:
        json.dump(memo, fp, indent=4)


if __name__ == "__main__":
    run()