try:
	from rdflib.graph import Graph
	from rdflib.term import Variable
except ImportError:
	from rdflib.Graph import Graph
	from rdflib import Variable
from rdflib.store import Store, VALID_STORE, NO_STORE
from rdflib.plugin import register
from _py4s import FourStoreClient, FourStoreError, _n3

__all__ = ["FourStore", "FourStoreError"]

class FourStore(FourStoreClient, Store):
	context_aware = True
	def __init__(self, configuration=None):
		self.__namespace = {}
		self.__prefix = {}
		if configuration:
			self.open(configuration)
	def bind(self, prefix, namespace):
		self.__namespace[prefix] = namespace
		self.__prefix[namespace] = prefix
	def namespace(self, prefix):
		return self.__namespace.get(prefix, None)
	def prefix(self, namespace):
		return self.__prefix.get(namespace, None)
	def namespaces(self):
		return self.__namespace.items()

	def query(self, *av, **kw):
		"""Execute a SPARQL Query"""
		return self.cursor().execute(*av, **kw)
	def add(self, *av, **kw):
		"""Add triples to the graph"""
		return self.cursor().add(*av, **kw)
	def addN(self, slist, **kw):
		"""Add a list of quads to the graph"""
		for s,p,o,c in slist:
			self.add((s,p,o), context=c, **kw)
	def remove(self, statement, context="local:"):
		"""Remove a triple from the graph"""
		if isinstance(context, Graph): _context = context.identifier
		else: _context = context
		s,p,o = statement
		bindings = (
			s or Variable("s"),
			p or Variable("p"),
			o or Variable("o")
		)

		construct = "CONSTRUCT { " + _n3(bindings) + " } WHERE { " 
		if _context and _context != "local:": construct += "GRAPH <%s> { " % _context
		construct += _n3(bindings)
		if _context and _context != "local:": construct += " }"
		construct += " }"

		result = self.cursor().execute(construct)

		delete = "DELETE { "
		if _context and _context != "local:": delete += "GRAPH <%s> { " % _context
		delete += " .\n".join(map(_n3, result.triples((None, None, None))))
		if _context and _context != "local:": delete += " }"
		delete += " }"

		self.cursor().update(delete)

	def __contains__(self, statement, context="local:"):
		if isinstance(context, Graph): _context = context.identifier
		else: _context = context
		query = "ASK WHERE { "
		if _context and _context != "local:": query += "GRAPH <%s> { " % _context
		query += " ".join([x.n3() for x in statement])
		if _context and _context != "local:": query += " }"
		query += " }"
		return bool(self.cursor().execute(query))

	def contexts(self, triple=None):
		if triple is None: triple = (None,None,None)
		s,p,o = triple
		bindings = (
			s or Variable("s"),
			p or Variable("p"),
			o or Variable("o")
		)
		query = "SELECT DISTINCT ?g WHERE { GRAPH ?g { "
		query += " ".join([x.n3() for x in bindings])
		query += " } }"
		for g, in self.query(query):
			yield Graph(self, identifier=g)

	def triples(self, statement, context="local:", **kw):
		"""Return triples matching (s,p,o) pattern"""

		## shortcut if we are just checking the existence
		if all(statement):
			if self.__contains__(statement, context):
				yield statement, context
			return

		if isinstance(context, Graph): _context = context.identifier
		else: _context = context
		s,p,o = statement
		bindings = (
			s or Variable("s"),
			p or Variable("p"),
			o or Variable("o")
		)
		query = "SELECT DISTINCT " + " ".join([x.n3() for x in bindings if isinstance(x, Variable)])
		query += " WHERE { "
		if _context and _context != "local:": query += "GRAPH <%s> { " % _context
		query += " ".join([x.n3() for x in bindings])
		if _context and _context != "local:": query += " }"
		query += " }"
		results = self.cursor().execute(query, **kw)
		for row in results:
			triple = []
			for b in bindings:
				if isinstance(b, Variable):
					triple.append(row[b])
				else:
					triple.append(b)
			yield (tuple(triple), context)

register("FourStore", Store, "py4s", "FourStore")
