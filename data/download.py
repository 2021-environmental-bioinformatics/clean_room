
from pangea_api import Knex, User, Organization

knex = Knex()
User(knex, "anmeyer@whoi.edu", "lacrosse2").login()
org = Organization(knex, "JPL Planetary Protection Group").idem()
grp = org.sample_group("JPL Clean Rooms").idem()
for sample in grp.get_samples(cache=False):
	for ar in sample.get_analysis_results(cache=False):
		if ar.module_name != '<module name>':
			continue		
	for field in ar.get_fields(cache=False):
		field.download_file(filename=filename)
