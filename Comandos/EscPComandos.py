# -*- coding: latin-1 -*-

import string
import types
import logging
import unicodedata
from ComandoInterface import ComandoInterface, ComandoException, ValidationError, FiscalPrinterError, formatText
from ConectorDriverComando import ConectorDriverComando
import time
from math import ceil


class PrinterException(Exception):
    pass

class EscPComandos(ComandoInterface):


	tipoCbte = {
	        "T": "Consumidor Final",
	        "FA":  "A", 
	        "FB": "Consumidor Final", 
	        "NDA": "NDA", 
	        "NCA": "NCA", 
	        "NDB": "NDB", 
	        "NCB": "NCB", 
	        "FC": "C", 
	        "NDC": "NCC",
	        "NDC": "NDC"

	}

	
	

	def __init__(self, deviceFile=None, driverName="ReceipDirectJet"):
		"deviceFile indica la IP o puerto donde se encuentra la impresora"
		self.conector = ConectorDriverComando(self, driverName, deviceFile)

	
	def _sendCommand(self, comando, skipStatusErrors=False):
		try:
			ret = self.conector.sendCommand(comando, skipStatusErrors)
			return ret
		except PrinterException, e:
			logging.getLogger().error("PrinterException: %s" % str(e))
			raise ComandoException("Error de la impresora: %s.\nComando enviado: %s" % \
				(str(e), commandString))

	
	def print_mesa_mozo(self, mesa, mozo):
		self.doble_alto_x_linea("Mesa: %s"%mesa);
		self.doble_alto_x_linea("Mozo: %s"%mozo);



	def printRemito(self, **kwargs):		
		"imprimir remito"
		encabezado = kwargs.get("encabezado", None)
		items = kwargs.get("items", [])
		addAdditional = kwargs.get("addAdditional", None)
		setTrailer = kwargs.get("setTrailer", None)

		printer = self.conector.driver

		printer.set("CENTER", "A", "A", 1, 1)
		
		# colocar en modo ESC P
		printer._raw(chr(0x1D)+chr(0xF9)+chr(0x35)+"1")

		printer.set("CENTER", "A", "A", 1, 1)
		printer.text( "Verifique su cuenta por favor\n" )
		printer.text( "COMPROBANTE NO VALIDO COMO FACTURA\n\n" )

		if encabezado:
			printer.set("CENTER", "A", "A", 1, 2)
			if encabezado.has_key("nombre_cliente"):
				printer.text( '\n%s\n\n'% encabezado.get("nombre_cliente") )

			if "fecha" in encabezado:
				printer.set("LEFT", "A", "A", 1, 1)
				fff_aux = time.strptime( encabezado['fecha'], "%Y-%m-%d %H:%M:%S")
				fecha = time.strftime('%H:%M %x', fff_aux)
				printer.text( fecha +"\n")

		printer.set("LEFT", "A", "A", 1, 1)
		

		printer.text("CANT\tDESCRIPCION\t\tPRECIO\n")
		printer.text("------------------------------------------\n")
		tot_chars = 40
		tot_importe = 0.0
		for item in items:
			desc = item.get('ds')[0:24]
			cant = item.get('qty')
			precio = item.get('importe')
			tot_importe += cant * float(precio)
			cant_tabs = 3
			can_tabs_final = cant_tabs - ceil( len(desc)/8 )
			strTabs = desc.ljust( int(len(desc) + can_tabs_final), '\t')

			printer.text("%g\t%s$%g\n" % (cant, strTabs, precio))

		printer.text("------------------------------------------\n")

		if addAdditional:
			#imprimir subtotal
			printer.set("RIGHT", "A", "A", 1, 1)
			printer.text("SUBTOTAL: $%g\n" % tot_importe)

			# imprimir descuento
			sAmount = float( addAdditional.get('amount',0) )
			tot_importe = tot_importe - sAmount
			printer.set("RIGHT", "A", "A", 1, 1)
			printer.text("%s $%g\n" % (addAdditional.get('description'), addAdditional.get('amount') ))

		# imprimir total
		printer.set("RIGHT", "A", "A", 2, 2)
		printer.text("\t\tTOTAL: $%g\n" % tot_importe)
		printer.text("\n\n\n")

		extra = kwargs.get("extra", None)
		if extra and "mesa_id" in extra:
			mesa_id = extra.get("mesa_id")
			printer.barcode(str(mesa_id).rjust(8,"0"),'EAN13')


		printer.set("CENTER", "A", "B", 1, 1)
		#plato principal
		if setTrailer:
			self._setTrailer(setTrailer)

		printer.cut("PART")

		# volver a poner en modo ESC Bematech, temporal para testing
		printer._raw(chr(0x1D)+chr(0xF9)+chr(0x35)+"0")


	def _setTrailer(self, setTrailer):
		print self.conector.driver		
		printer = self.conector.driver

		for trailerLine in setTrailer:
			if trailerLine:
				printer.text( trailerLine )

			printer.text( "\n" )
		

	def printComanda(self, comanda, setHeader=None, setTrailer=None):
		"observacion, entradas{observacion, cant, nombre, sabores}, platos{observacion, cant, nombre, sabores}"
		print self.conector.driver		
		printer = self.conector.driver

		# 0x1D 0xF9 0x35 1
		# colocar en modo ESC P
		printer._raw(chr(0x1D)+chr(0xF9)+chr(0x35)+"1")

		if setHeader:
			for headerLine in setHeader:
				printer.text( headerLine )	

		printer.set("CENTER", "A", "A", 1, 1)
		printer.text("Comanda #%s\n" % comanda['id'])

		fff_aux = time.strptime( comanda['created'], "%Y-%m-%d %H:%M:%S")
		fecha = time.strftime('%H:%M %x', fff_aux)

		#fecha = datetime.strftime(comanda['created'], '%Y-%m-%d %H:%M:%S')
		printer.text( fecha +"\n")


		def print_plato(plato):
			"Imprimir platos"
			printer.set("LEFT", "A", "B", 1, 2)

			printer.text( "%s) %s"%( plato['cant'], plato['nombre']) )

			if 'sabores' in plato:
				printer.set("LEFT", "A", "B", 1, 1)
				text = "(%s)" % ", ".join(plato['sabores'])
				printer.text( text )
			
			printer.text("\n")

			if 'observacion' in plato:
				printer.set("LEFT", "B", "B", 1, 1)
				printer.text( "   OBS: %s\n" % plato['observacion'] )

		
		printer.text( "\n")

		if 'observacion' in comanda:
			printer.set( "CENTER", "B", "B", 2, 2)
			printer.text( "OBSERVACION\n")
			printer.text( comanda['observacion'] )
			printer.text( "\n")
			printer.text( "\n")


		if 'entradas' in comanda:
			printer.set("CENTER", "A", "B", 1, 1)
			printer.text( "** ENTRADA **\n" )

			for entrada in comanda['entradas']:
				print_plato(entrada)

			printer.text( "\n\n" )

		if 'platos' in comanda:
			printer.set("CENTER", "A", "B", 1, 1)
			printer.text( "----- PRINCIPAL -----\n" )

			for plato in comanda['platos']:
				print_plato(plato)
			printer.text( "\n\n" )

		#plato principal
		if setTrailer:
			self._setTrailer(setTrailer)
		

		printer.cut("PART")

		# volver a poner en modo ESC Bematech, temporal para testing
		printer._raw(chr(0x1D)+chr(0xF9)+chr(0x35)+"0")
		

	