# This module will handle all the input/output of the code (at least most of
# it). 

# So if something is printed that does not satisfy you (number of decimals, for
# instance), you only have to find the called function and change a number.

import os,sys
import re     # Module to handle regular expressions (powerful tool to manipulate strings)
import random as rd
import numpy as np
try:
  from collections import OrderedDict as od
except:
  from ordereddict import OrderedDict as od    
from datetime import date
from common import lock,LockException
import fcntl

# Writes the beginning of log.param, starting with the header with the
# cosmological code version and subversion, and then recopies entirely the
# input parameter file
def log_parameters(data,command_line):
  log     = open(command_line.folder+'/log.param','w')
  param_file = open(command_line.param,'r')
  log.write("#-----{0} {1} (subversion {2})-----\n\n".format(data.cosmological_module_name,data.version,data.subversion))
  for line in param_file:
    log.write(line)
  param_file.close()
  log.close()

# Writes the configuration for each and every likelihood used
def log_likelihood_parameters(likelihood,command_line):
  log = open(command_line.folder+'log.param','a')
  tolog = open(likelihood.path,'r')
  log.write("\n\n#-----Likelihood-{0}-----\n".format(likelihood.name))
  for line in tolog:
    log.write(line)
  tolog.seek(0)
  tolog.close()
  log.close()

# Third function called when writing log.param, it writes down the
# cosmo_arguments used (it is understood here that all the other parameters for
# the cosmological modules are set to their default value directly in the
# program). It is written as an update for the dictionary cosmo_arguments, in
# order not to erase previously initialized data.
def log_cosmo_arguments(data,command_line):
  if len(data.cosmo_arguments) >= 1:
    log     = open(command_line.folder+'/log.param','a')
    log.write('\n\n#-----------Cosmological-arguments---------\n')
    log.write('data.cosmo_arguments.update({0})\n'.format(data.cosmo_arguments))
    log.close()

# Fourth and last function called when writing log.param, it logs the .conf
# file used to get the path. Only useful if you have several versions of your
# cosmological code installed in different locations, or different versions of
# Clik. But, as you never know what might go wrong, it is logged everytime !
def log_default_configuration(data,command_line):
  log = open(command_line.folder+'/log.param','a')
  log.write('\n\n#--------Default-Configuration------\n')
  for key,value in data.path.iteritems():
    log.write("data.path['{0}']\t= '{1}'\n".format(key,value))
  log.close()

# Will print the parameter names. In the code, out is simply the standard
# output, as this information will not be printed on the output file. Indeed,
# you will be able to recover these information from the log.param. Please pay
# attention to the fact that, once launched, the order of the parameters in
# log.param is crucial, as is it the only place where it is stored.
def print_parameters(out,data):
  param = data.get_mcmc_parameters(['varying'])
  for elem in data.get_mcmc_parameters(['derived']):
    param.append(elem)
  out.write('\n#  -LogLkl\t')
  for i in range(len(param)):
    if data.mcmc_parameters[param[i]]['scale']!=1:
      number = data.mcmc_parameters[param[i]]['scale']
      if (number > 100. or number < 0.01):
	string = '%0.e%s' % (1./number,param[i])
      else:
	string = '%0.2g%s' % (1./number,param[i])
    else:
      string = '%s' % param[i]
    out.write("%-16s" % string)
  out.write('\n')

# Prints the last accepted values to out, which here is an array containing
# both standard output and the output file. This way, if you run in interactive
# mode, you will be able to monitor the progress of the chain.
def print_vector(out,N,loglkl,data):
  for j in range(len(out)):
    out[j].write('%d  %.6g\t' % (N,-loglkl))
    for elem in data.get_mcmc_parameters(['varying']):
      out[j].write('%.6e\t' % data.mcmc_parameters[elem]['last_accepted'])
    for elem in data.get_mcmc_parameters(['derived']):
      out[j].write('%.6e\t' % data.mcmc_parameters[elem]['last_accepted'])
    out[j].write('\n')

def refresh_file(data):
  data.out.close()
  data.out=open(data.out_name,'a')

# This routine takes care of organising the folder for you. It will
# automatically generate names for the new chains according to the date, number
# of points chosen.
###################
# VERY IMPORTANT
###################
# The way these names are generated (with the proper number of _, __, -, and
# their placement) is exploited in the rest of the code in various places.
# Please keep that in mind if ever you are in the mood of changing things here.
def create_output_files(command_line,data):
  if command_line.restart is None:
    number = command_line.N
  else:
    number = int(command_line.restart.split('/')[-1].split('__')[0].split('_')[1]) + command_line.N

  # output file
  outname_base='{0}_{1}__'.format(date.today(),number)
  suffix=0
  Try = True
  if command_line.chain_number is None:
    for files in os.listdir(command_line.folder):
      if files.find(outname_base)!=-1:
        if int(files.split('__')[-1].split('.')[0])>suffix:
          suffix=int(files.split('__')[-1].split('.')[0])
    suffix+=1
    while Try:
      data.out = open(command_line.folder+outname_base+str(suffix)+'.txt','w')
      try:
        lock(data.out, fcntl.LOCK_EX | fcntl.LOCK_NB)
        Try = False
      except LockException:
        suffix+=1
    sys.stdout.write('Creating {0}{1}{2}.txt\n'.format(command_line.folder,outname_base,suffix))
    data.out_name='{0}{1}{2}.txt'.format(command_line.folder,outname_base,suffix)
  else:
    data.out=open(command_line.folder+outname_base+command_line.chain_number+'.txt','w')
    sys.stdout.write('Creating {0}{1}{2}.txt\n'.format(command_line.folder,outname_base,command_line.chain_number))
    data.out_name='{0}{1}{2}.txt'.format(command_line.folder,outname_base,command_line.chain_number)
  # in case of a restart, copying the whole thing in the new file
  if command_line.restart is not None:
    for line in open(command_line.restart,'r'):
      data.out.write(line)

# Simple tex name transformer. 
def get_tex_name(name,number=1):
  tex_greek = ['omega','tau','alpha','beta','delta','nu','Omega','Lambda','lambda']
  for elem in tex_greek:
    if elem in name:
      position = name.find(elem)
      name=name[:position]+"""\\"""+name[position:]
  if name.find('_')!=-1:
    temp_name = name.split('_')[0]+'_{'
    for i in range(1,len(name.split('_'))):
      temp_name += name.split('_')[i]+' '
    name = temp_name + '}'
  if number==1: 
    name = "${0}$".format(name)
  elif (number < 1000 and number > 1):
    name = "$%0.d~%s$" % (number,name)
  else:
    temp_name = "$%0.e%s$" % (number,name)
    m = re.search(r'(?:\$[0-9]*e\+[0]*)([0-9]*)(.*)',temp_name)
    sign = '+'
    if m == None:
      m = re.search(r'(?:\$[0-9]*e\-[0]*)([0-9]*)(.*)',temp_name)
      sign = '-'
    name = '$10^{'+sign+m.groups()[0]+'}'+m.groups()[1]
  return name

# New class of file, to provide an equivalent of the tail command (on linux).
# It will be used when starting from an existing chain, and avoids circling
# through an immense file. 
class File(file):

  def tail(self, lines_2find=1):  
    self.seek(0, 2)                         #go to end of file
    bytes_in_file = self.tell()             
    lines_found, total_bytes_scanned = 0, 0
    while (lines_2find+1 > lines_found and
       bytes_in_file > total_bytes_scanned): 
      byte_block = min(1024, bytes_in_file-total_bytes_scanned)
      self.seek(-(byte_block+total_bytes_scanned), 2)
      total_bytes_scanned += byte_block
      lines_found += self.read(1024).count('\n')
    self.seek(-total_bytes_scanned, 2)
    line_list = list(self.readlines())
    return line_list[-lines_2find:]