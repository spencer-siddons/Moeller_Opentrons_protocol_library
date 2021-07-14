from opentrons import protocol_api
from opentrons_functions.magbeads import (
    remove_supernatant, bead_wash)
from opentrons_functions.transfer import add_buffer

#def run(protocol):
    
metadata = {'protocolName': 'MYLF Protocol',
    'author': 'Spencer Siddons <ssiddon@purdue.edu>',
    'description': 'Protocol with Zymo QuickDNA Kit Cat. No. D6010-FM',
    'apiLevel': '2.5'}

# Set to `True` to perform a short run, with brief pauses and only
# one column of samples
test_run = True

#pip install https://github.com/tanaes/opentrons_functions/archive/v0.2.6-prerelease.tar.gz
#pip install https://github.com/tanaes/opentrons_functions/archive/v0.1.0-prerelease.tar.gz

if test_run:
    pause_bind = 5
    pause_mag = 3
    pause_dry = 5
    pause_elute = 5

    # Limit columns
    cols = ['A1', 'A2']
else:
    pause_bind = 5*60
    pause_mag = 3*60
    pause_dry = 5*60
    pause_elute = 5*60

    # Limit columns
    cols = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6',
            'A7', 'A8', 'A9', 'A10', 'A11', 'A12']

# define magnet engagement height for plates
# (none if using labware with built-in specs)
mag_engage_height = 6


# MagBinding + beads cols
mbb_cols = ['A1', 'A2', 'A3', 'A4']

# MagBinding cols
mbw_cols = ['A5', 'A6', 'A7']

# Wash 1 columns
w1_cols = ['A1', 'A2', 'A3']

# Wash 2 columns
w2_cols = ['A4', 'A5', 'A6', 'A7', 'A8', 'A9',
           'A10', 'A11', 'A12']

# bead aspiration flow rate
bead_flow = .25

# wash mix mutliplier
wash_mix = 5


def run(protocol: protocol_api.ProtocolContext):

    # ### Setup

    # define deck positions and labware

    # define hardware modules
    magblock = protocol.load_module('Magnetic Module gen2', 10)
    magblock.disengage()

    # tips
    tiprack_buffers = protocol.load_labware('opentrons_96_tiprack_300ul',
                                            8)
    tiprack_elution_1 = protocol.load_labware(
                            'opentrons_96_filtertiprack_200ul', 5)
    tiprack_elution_2 = protocol.load_labware(
                            'opentrons_96_filtertiprack_200ul', 6)
    tiprack_wash = protocol.load_labware('opentrons_96_tiprack_300ul',
                                         4)

    # plates
    wash_buffers = protocol.load_labware('nest_12_reservoir_15ml',
                                         11, 'wash buffers')#the reservoir labware was changed from: usascientific_12_reservoir_22ml
    eluate = protocol.load_labware('biorad_96_wellplate_200ul_pcr',
                                   3, 'eluate')
    waste = protocol.load_labware('nest_1_reservoir_195ml',
                                  7, 'liquid waste')
    reagents = protocol.load_labware('nest_12_reservoir_15ml',
                                     9, 'reagents')#the reservoir labware was changed from: usascientific_12_reservoir_22ml

    # load plate on magdeck
    # mag_plate = magblock.load_labware('vwr_96_wellplate_1000ul')
    mag_plate = magblock.load_labware('vwr_96_wellplate_1000ul')

    # initialize pipettes - is this a GEN1 or GEN2 pipette? Can still be run if gen2 (protocol in opentrons specifies it as gen1 but with an "inexact" warning)
    pipette_right = protocol.load_instrument('p300_multi_gen2',
                                            'right',
                                            tip_racks=[tiprack_buffers])

    # MagBindingBuffer + beads wells
    mbb_wells = [reagents[x] for x in mbb_cols]

    # MagBindingBuffer wells
    mbw_wells = [reagents[x] for x in mbw_cols]

    # Wash 1 columns
    w1_wells = [wash_buffers[x] for x in w1_cols]

    # Wash 2 columns
    w2_wells = [wash_buffers[x] for x in w2_cols]

    # ### Prompt user to place plate on mag block
    protocol.pause('Add plate containing 200 µL per well of lysis supernatant'
                   ' onto the magdeck in position 10.')

    # ### Add MagBinding buffer and beads to plate
    protocol.comment('Adding beads to plate.')

    # add beads
    mbb_remaining, mbb_wells = add_buffer(pipette_right,
                                          mbb_wells,
                                          mag_plate,
                                          cols,
                                          625,
                                          18000/8,
                                          pre_mix=10)

    # mix beads and samples
    for col in cols:
        pipette_right.pick_up_tip(tiprack_wash.wells_by_name()[col])
        pipette_right.mix(10, 250, mag_plate[col].bottom(z=1))
        pipette_right.blow_out(mag_plate[col].top(z=-2))
        pipette_right.touch_tip()#looks like there is an error here. Still running but not moving forward in steps
        pipette_right.return_tip()#putting tips back into the tip box

    # bind to beads
    protocol.comment('Binding DNA to beads.')
    protocol.delay(seconds=pause_bind)#defined somewhere else in terms of time

    # mix again
    for col in cols:
        pipette_right.pick_up_tip(tiprack_wash.wells_by_name()[col])
        pipette_right.mix(10, 250, mag_plate[col].bottom(z=1))
        pipette_right.blow_out(mag_plate[col].top(z=-2))
        pipette_right.touch_tip()
        pipette_right.return_tip()#putting tips back into the tip box

    # bind to magnet
    protocol.comment('Binding beads to magnet.')
    magblock.engage(height_from_base=mag_engage_height)

    protocol.delay(seconds=pause_mag)#according to kit protocol: shake 1200rpm for 10 min, stand for 2 min (steps 10-11)

    # ### Do first wash: Wash 500 µL MagBinding buffer -- looks like doplets after every dispense. Add "pipette_right.touch_tip()""?
    protocol.comment('Doing wash #1.')
    mbw_remaining, mbw_wells = bead_wash(
                                         # global arguments
                                         protocol,
                                         magblock,
                                         pipette_right,
                                         mag_plate,
                                         cols,
                                         # super arguments - looks like droplets here afte dispensing into waste. Maybe add: "pipette_right.blow_out(mag_plate[col].top())" and to those below
                                         waste['A1'],
                                         tiprack_wash,
                                         # wash buffer arguments,
                                         mbw_wells,
                                         19000/8,
                                         # mix arguments
                                         tiprack_wash,
                                         # optional arguments
                                         wash_vol=500,
                                         super_vol=800,
                                         pipette.air_gap(10),
                                         drop_super_tip=False,
                                         mix_n=wash_mix,
                                         mag_engage_height=mag_engage_height)

    # ### Do second wash: Wash 500 µL MagWash 1
    protocol.comment('Doing wash #2.')
    w1_remaining, w1_wells = bead_wash(
                                       # global arguments
                                       protocol,
                                       magblock,
                                       pipette_right,
                                       mag_plate,
                                       cols,
                                       # super arguments
                                       waste['A1'],
                                       tiprack_wash,
                                       # wash buffer arguments
                                       w1_wells,
                                       19000/8,
                                       # mix arguments
                                       tiprack_wash,
                                       # optional arguments,
                                       wash_vol=500,
                                       super_vol=500,
                                       pipette.air_gap(10),
                                       drop_super_tip=False,
                                       mix_n=wash_mix,
                                       remaining=None,
                                       mag_engage_height=mag_engage_height)

    # ### Do third wash: Wash 900 µL MagWash 2
    protocol.comment('Doing wash #3.')
    w2_remaining, w2_wells = bead_wash(
                                       # global arguments
                                       protocol,
                                       magblock,
                                       pipette_right,
                                       mag_plate,
                                       cols,
                                       # super arguments
                                       waste['A1'],
                                       tiprack_wash,
                                       # wash buffer arguments
                                       w2_wells,
                                       21000/8,
                                       # mix arguments
                                       tiprack_wash,
                                       # optional arguments,
                                       wash_vol=900,
                                       super_vol=500,
                                       pipette.air_gap(10),
                                       drop_super_tip=False,
                                       mix_n=wash_mix,
                                       remaining=None,
                                       mag_engage_height=mag_engage_height)

    # ### Do fourth wash: Wash 900 µL MagWash 2
    protocol.comment('Doing wash #4.')
    w2_remaining, w2_wells = bead_wash(
                                       # global arguments
                                       protocol,
                                       magblock,
                                       pipette_right,
                                       mag_plate,
                                       cols,
                                       # super arguments
                                       waste['A1'],
                                       tiprack_wash,
                                       # wash buffer arguments
                                       w2_wells,
                                       21000/8,
                                       # mix arguments
                                       tiprack_wash,
                                       # optional arguments,
                                       wash_vol=900,
                                       super_vol=900,
                                       pipette.air_gap(10),
                                       drop_super_tip=False,
                                       mix_n=wash_mix,
                                       remaining=w2_remaining,
                                       mag_engage_height=mag_engage_height)

    # ### Dry
    protocol.comment('Removing wash and drying beads.')

    # This should:
    # - pick up tip in position 8
    # - pick up supernatant from magplate
    # - dispense in waste, position 11
    # - repeat
    # - trash tip
    # - leave magnet engaged

    # remove supernatant
    remove_supernatant(pipette_right,
                       mag_plate,
                       cols,
                       tiprack_wash,
                       waste['A1'],
                       super_vol=1000,
                       rate=bead_flow,
                       bottom_offset=.5,
                       drop_tip=True)

    # dry
    protocol.delay(seconds=pause_dry)#dry for 5 minutes

    # ### Elute-- this is where we want to get the supernatant because that's where the dna will be
    protocol.comment('Eluting DNA from beads.')

    # This should:
    # - disengage magnet
    # - pick up tip from position 6
    # - pick up reagents from column 2 of position 9
    # - dispense into magplate
    # - mix 10 times
    # - blow out, touch tip
    # - return tip to position 6
    # - wait (5 seconds)
    # - engage magnet
    # - wait (5 seconds)
    # - pick up tip from position 6
    # - aspirate from magplate
    # - dispense to position 3
    # - trash tip

    # transfer elution buffer to mag plate
    magblock.disengage()

    # add elution buffer and mix
    for col in cols:
        pipette_right.pick_up_tip(tiprack_elution_1.wells_by_name()[col])
        pipette_right.aspirate(50, reagents['A8'], rate=1)
        pipette_right.dispense(50, mag_plate[col].bottom(z=1))
        pipette_right.mix(10, 40, mag_plate[col].bottom(z=1))
        pipette_right.blow_out(mag_plate[col].top())
        pipette_right.touch_tip()
        # we'll use these same tips for final transfer
        pipette_right.return_tip()

    protocol.delay(seconds=pause_elute)
    # # start timer
    # t0 = clock()
    # # mix again
    # t_mix = 0
    # while t_mix < pause_elute():
    for col in cols:
        pipette_right.pick_up_tip(tiprack_elution_1.wells_by_name()[col])
        pipette_right.mix(10, 40, mag_plate[col].bottom(z=1))
        pipette_right.blow_out(mag_plate[col].top())
        pipette_right.touch_tip()
        # we'll use these same tips for final transfer
        pipette_right.return_tip()
        # t_mix = clock() - t0

    # bind to magnet
    protocol.comment('Binding beads to magnet.')

    magblock.engage(height_from_base=mag_engage_height)

    protocol.delay(seconds=pause_mag)

    protocol.comment('Transferring eluted DNA to final plate.')
    for col in cols:
        pipette_right.pick_up_tip(tiprack_elution_2.wells_by_name()[col])
        pipette_right.aspirate(50,
                              mag_plate[col].bottom(z=2),
                              rate=bead_flow)
        pipette_right.dispense(50, eluate[col])
        pipette_right.blow_out(eluate[col].top())
        pipette_right.touch_tip()
        # we're done with these tips now
        pipette_right.drop_tip()

    magblock.disengage()
