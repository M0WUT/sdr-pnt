# SFP
The SFP connector on the timing reference is a complete abuse of the standard in that it is just used as an LVDS to optical converter. The advantage of this is that the frequency reference being distributed can be distributed from a single (ideally) GPS locked reference to over arbitrarily large distances without issues introduced by interference or signal attenuation induced by running large lengths of coax.

For full details on Primary vs Secondary references see @TODO section of this repo.

A Primary Reference will use only the TX pair in the SFP to transmit the frequency reference. 

A Secondary Reference will only use the RX pair to receive the signal transmitted by a Primary Reference.


## Primary SFP Logic Flowchart
![Flowchart for SFP control on a Primary Reference](SFP_Primary.drawio.svg)