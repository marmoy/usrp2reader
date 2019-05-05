#!/usr/bin/env python
#Developed by: Michael Buettner (buettner@cs.washington.edu)
#Modified for USRP2 by: Yuanqing Zheng (yuanqing1@ntu.edu.sg)

#from gnuradio import digital
#from gnuradio import eng_notation
from gnuradio import gr,gru
from gnuradio import uhd
from gnuradio.wxgui import scopesink2
from gnuradio.wxgui import scopesink2
from gnuradio.eng_option import eng_option
from gnuradio.gr import firdes
from grc_gnuradio import wxgui as grc_wxgui
from optparse import OptionParser
from string import split
from string import strip
from string import atoi
import time
import os
import math
import rfid
import wx
from threading import Timer


log_file = open("log_out.log", "a")


class top_block(grc_wxgui.top_block_gui):

	def __init__(self):
		grc_wxgui.top_block_gui.__init__(self, title="Grc Wisp Reader")
		_icon_path = "/usr/share/icons/hicolor/32x32/apps/gnuradio-grc.png"
		self.SetIcon(wx.Icon(_icon_path, wx.BITMAP_TYPE_ANY))
		
		self.wxgui_scopesink2_0 = scopesink2.scope_sink_f(
			self.GetWin(),
			title="Scope Plot",
			sample_rate=1e6,
			v_scale=0,
			v_offset=0,
			t_scale=0,
			ac_couple=False,
			xy_mode=False,
			num_inputs=1,
			trig_mode=gr.gr_TRIG_MODE_AUTO,
			y_axis_label="Counts",
		)
		self.Add(self.wxgui_scopesink2_0.win)
           
		amplitude = 1


		interp_rate = 128
#		dec_rate = 8
#		sw_dec = 4
		dec_rate = 16
		sw_dec = 2

#		num_taps = int(64000 / ( (dec_rate * 4) * 40 )) #Filter matched to 1/4 of the 40 kHz tag cycle
		num_taps = int(64000 / ( (dec_rate * 4) * 256 )) #Filter matched to 1/4 of the 256 kHz tag cycle

		taps = [complex(1,1)] * num_taps
		
		matched_filt = gr.fir_filter_ccc(sw_dec, taps);
		  
		agc = gr.agc2_cc(0.3, 1e-3, 1, 1, 100) 
	     
		to_mag = gr.complex_to_mag()
#		center = rfid.center_ff(10)
		center = rfid.center_ff(4)

		omega = 5
		mu = 0.25
		gain_mu = 0.25
		gain_omega = .25 * gain_mu * gain_mu
		omega_relative_limit = .05

#		mm = digital.clock_recovery_mm_ff(omega, gain_omega, mu, gain_mu, omega_relative_limit)
		mm = rfid.clock_recovery_zc_ff(4,1);
		self.reader = rfid.reader_f(int(128e6/interp_rate)); 
		
		tag_decoder = rfid.tag_decoder_f()
		
#		command_gate = rfid.command_gate_cc(12, 250, 64000000 / dec_rate / sw_dec)
		command_gate = rfid.command_gate_cc(12, 60, 64000000 / dec_rate / sw_dec)
		

	       
	       
		to_complex = gr.float_to_complex()
		amp = gr.multiply_const_ff(amplitude)
		
		##################################################
		# Blocks
		##################################################
		freq = 915e6
		rx_gain = 1

		tx = uhd.usrp_sink(
			device_addr="",
			io_type=uhd.io_type.COMPLEX_FLOAT32,
			num_channels=1,
		)
		print "tx: get sample rate:"
		print (tx.get_samp_rate())
		tx.set_samp_rate(128e6/interp_rate)
		print "tx: get sample rate:"
		print (tx.get_samp_rate())
		
		r = tx.set_center_freq(freq, 0)
		
		rx = uhd.usrp_source(
			device_addr="",
			io_type=uhd.io_type.COMPLEX_FLOAT32,
			num_channels=1,
		)
		print "rx: get samp rate"
		print (rx.get_samp_rate())		
		r = rx.set_samp_rate(64e6/dec_rate)
		print "rx: get samp rate"
		print (rx.get_samp_rate())		

		r = rx.set_center_freq(freq, 0)
		
		print "rx: get gain "
		print (rx.get_gain_range())		
		r = rx.set_gain(rx_gain, 0)
		print "rx: get gain "
		print (rx.get_gain())		


		command_gate.set_ctrl_out(self.reader.ctrl_q())
		tag_decoder.set_ctrl_out(self.reader.ctrl_q())

	#########Build Graph
		self.connect(rx, matched_filt)		
		self.connect(matched_filt, command_gate)


		self.connect(command_gate, to_mag)
#		self.connect(command_gate, agc)
#		self.connect(agc, to_mag) 

		self.connect(to_mag, center, mm, tag_decoder)
#		self.connect(to_mag, center, matched_filt_tag_decode, tag_decoder)
		self.connect(tag_decoder, self.reader)
		self.connect(self.reader, amp)	
		self.connect(amp, to_complex)
		self.connect(to_complex, tx)

	#################
		

def main():
    
#    gr.enable_realtime_scheduling()
    tb = top_block()
    
    tb.Run(True)
    while 1:
        
        c = raw_input("'Q' to quit. L to get log.\n")
        if c == "q":
            break
        
        if c == "L" or c == "l":
            log_file.write("T,CMD,ERROR,BITS,SNR\n")
            log = tb.reader.get_log()
            print "Log has %s Entries"% (str(log.count()))
            i = log.count();
            
            
            for k in range(0, i):
                msg = log.delete_head_nowait()
                print_log_msg(msg, log_file)
                
    tb.Stop(True)
    
def print_log_msg(msg, log_file):
    LOG_START_CYCLE, LOG_QUERY, LOG_ACK, LOG_QREP, LOG_NAK, LOG_REQ_RN, LOG_READ, LOG_RN16, LOG_EPC, LOG_HANDLE, LOG_DATA, LOG_EMPTY, LOG_COLLISION, LOG_OKAY, LOG_ERROR = range(15)
 

    fRed = chr(27) + '[31m'
    fBlue = chr(27) + '[34m'
    fReset = chr(27) + '[0m'


    if msg.type() == LOG_START_CYCLE:
        fields = split(strip(msg.to_string()), " ")
        print "%s\t Started Cycle" %(fields[-1]) 
        log_file.write(fields[-1] + ",START_CYCLE,0,0,0\n");

    if msg.type() == LOG_QUERY:
        fields = split(strip(msg.to_string()), " ")
        print "%s\t Query" %(fields[-1]) 
        log_file.write(fields[-1] + ",QUERY,0,0,0\n");

    if msg.type() == LOG_QREP:
        fields = split(strip(msg.to_string()), " ")
        print "%s\t QRep" %(fields[-1]) 
        log_file.write(fields[-1] + ",QREP,0,0,0\n");

    if msg.type() == LOG_ACK:
        fields = split(strip(msg.to_string()), " ")
        print "%s\t ACK" %(fields[-1])
        log_file.write(fields[-1] + ",ACK,0,0,0\n");

    if msg.type() == LOG_NAK:
        fields = split(strip(msg.to_string()), " ")
        print "%s\t NAK" %(fields[-1])
        log_file.write(fields[-1] + ",NAK,0,0,0\n");

    
    if msg.type() == LOG_RN16:
        fields = split(strip(msg.to_string()), " ")
        rn16 = fields[0].split(",")[0]
        snr = strip(fields[0].split(",")[1])
        tmp = int(rn16,2)
       
        if msg.arg2() == LOG_ERROR:
            
            print "%s\t    %s RN16 w/ Error: %04X%s" %(fields[-1],fRed, tmp, fReset)
            log_file.write(fields[-1] + ",RN16,1," +"%04X" % tmp  + ","+snr + "\n");
        else:
            print "%s\t    %s RN16: %04X%s" %(fields[-1],fBlue, tmp, fReset)
            log_file.write(fields[-1] +",RN16,0," + "%04X" % tmp + "," +snr + "\n");
        
        
    if msg.type() == LOG_EPC:
        fields = split(strip(msg.to_string()), " ")
        epc = fields[0].split(",")[0]
        snr = strip(fields[0].split(",")[1])
        epc = epc[16:112]

        tmp = int(epc,2)
        if msg.arg2() == LOG_ERROR:
            print "%s\t    %s EPC w/ Error: %024X%s" %(fields[-1],fRed, tmp, fReset)
            log_file.write(fields[-1] + ",EPC,1," + "%024X" % tmp + ","+snr + "\n");
        else:
            print "%s\t    %s EPC: %024X%s" %(fields[-1],fBlue, tmp, fReset)
            log_file.write(fields[-1] +",EPC,0," + "%024X" % tmp + "," +snr + "\n");

    if msg.type() == LOG_EMPTY:
        fields = split(strip(msg.to_string()), " ")
        snr = strip(fields[0])
        print "%s\t    - Empty Slot - " %(fields[-1]) 
        log_file.write(fields[-1] + ",EMPTY,0,0,"+snr+"\n");

    if msg.type() == LOG_COLLISION:
        fields = split(strip(msg.to_string()), " ")
        print "%s\t    - Collision - " %(fields[-1]) 
        log_file.write(fields[-1] + ",COLLISION,0,0,0\n");


if __name__ == '__main__':
    main()


