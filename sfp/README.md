# SFP
The SFP connector on the timing reference is a complete abuse of the standard in that it is just used as an LVDS to optical converter. The advantage of this is that the frequency reference being distributed can be distributed from a single (ideally) GPS locked reference to over arbitrarily large distances without issues introduced by interference or signal attenuation induced by running large lengths of coax.

For full details on Primary vs Secondary references see @TODO section of this repo.

For full details on Warnings and Errors see @TODO section of this repo.

Further details on the SFP standard can be found [here](http://www.schelto.com/SFP/SFP%20MSA.pdf). FYI I'm not sure how legitimate this link is in terms of leaking a standard. Use at your own risk!

A Primary Reference will use only the TX pair in the SFP to transmit the frequency reference. 

A Secondary Reference will only use the RX pair to receive the signal transmitted by a Primary Reference.


## Primary SFP Logic Flowchart
The logic for a Primary Reference is fairly straightforward. If an SFP connector is plugged in, operating correctly and we have a valid reference, then use it to transmit. In case of any issue, wait until it's unplugged and something is re-inserted and try again. The logic for handling what signalling needs to happen when the internal reference goes invalid is handled in internal_ref.py and is not a concern here.

![Flowchart for SFP control on a Primary Reference](SFP_Primary.drawio.svg)