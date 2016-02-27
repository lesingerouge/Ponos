# system imports
import os,json
# framework imports
# app imports



class DataTableHelper(object):

	#used in case there are fields that do should not appear in a table
	show_fields = None
	#used if a row can be expanded and show more details about an entry
	expand_fields = None
	#used if a row has a field dedicated to buttons
	button_field = False
	
	@classmethod
	def _process_request(cls,request):

		query_values = {}
		sorting_values = []
		limit_results = 0
		skip_results = 0

		if request.get("start"):
			skip_results = int(request.get("start"))

		if request.get("lenght"):
			limit_results = int(request.get("length"))

		# if 'order' in request.form:
		# 	for item in request.form['order']:
		# 		direction = 1 if item[1] == 'asc' else -1
		# 		temp = getattr(cls,request.form['columns'][item[0]][1])
		# 		sorting_values.append((temp.dbfield,direction))

		# if 'search' in request.form:
		# 	for item in request.form['columns']:
		# 		if item[2] and item[4][0]:
		# 			temp = getattr(cls,item[1])
		# 			query_values[temp.dbfield] = item[4][0]

		return query_values, sorting_values, limit_results, skip_results


	@classmethod
	def to_tables(cls,request):

		query_values, sorting_values, limit_results, skip_results = cls._process_request(request)

		result_data = cls.db[cls.collection].find(filter=query_values,sort=sorting_values,skip=skip_results,limit=limit_results)

		output = []
		if result_data:
			for item in result_data:
				output.append(cls(values=item))

		return output


	@classmethod
	def to_datatables(cls,request,no_objects=False):

		result_data = cls.to_tables(request)

		output = {}
		output['draw'] = request['draw']
		output['recordsTotal'] = int(cls.db[cls.collection].count())
		output['recordsFiltered'] = int(len(result_data))
		output['data'] = []

		if result_data:
			for item in result_data:
				values = item.to_dict()

				if "_id" in values:
					values.update({"DT_RowId":str(values["_id"])})
					del values["_id"]
					
				if cls.show_fields:
					_values = {x:values[x] for x in values if x in cls.show_fields or x == "DT_RowId"}
					values = _values
	
				if cls.expand_fields:
					values["details"] = {x:values[x] for x in cls.expand_fields}
					for x in cls.expand_fields:
						del values[x]

				if cls.button_field:
					values["actiuni"] = values["DT_RowId"]

				if no_objects:
					if cls.show_fields:
						output['data'].append([values[x] for x in cls.show_fields])
					else:
						output['data'].append([values[x] for x in values])
				else:
					output['data'].append(values)

		return output


	@classmethod
	def table_head(cls):

		result = []
		for x in cls.show_fields:
			if cls.fromdict:
				for item in cls.fromdict:
					if item == x:
						temp = cls.fromdict.get(item)
						result.append(temp["verbose"])

		if cls.button_field:
			result.append("Actiuni")

		return result


	@classmethod
	def datatables_columns(cls):

		result = []
		for x in cls.show_fields:
			if cls.fromdict:
				for item in cls.fromdict:
					if item == x:
						temp = cls.fromdict.get(item)
						result.append({"data":temp["dbfield"]})

		if cls.button_field:
			result.append({"data":"actiuni"})

		return json.dumps(result)

