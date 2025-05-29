# Unreal Flooding Scripts

# Requirements:
- Unreal Engine >= 5.4
- Fluidflux >= 3.0
- Conda

# Supplied/required data:
`\\file\Research\FloodRiskResearch\Xander\Luke\taumutu_data`
- Flood model output
- Points to query flood depth
- Unreal level boundary

# Steps required:
1. Install conda environment
    `conda env create -f environment.yml`
2. Create CSV file from flood model: 
    Run `create_water_csv.py`
3. Modify Unreal editor default parameters for water source:
   1. Open `/Content/FluidFlux/Simulation/Modifiers/BP_FluxModifierSourceActor.uasset`
   2. Select `FluxModifierSource` in the components tab
   3. Set `Mode=SET` and `Duration=-1` in the details tab - these do not seem to be able to be set by python.
4. Create a Fluid Flux simulation domain according to Fluid Flux docs
5. Add water sources by executing `Unreal Editor > Tools > Execute Python Script > ... / spawn_water.py`


# Important Notes:

- Python scripting does not seem to be able to modify Duration or Mode for a water source.
- `spawn_water.py` has variables `Z_TERRAIN_SCALE_FACTOR` and `Z_TERRAIN_INTERCEPT` which are hand-calibrated to align Unreal Landscapes with real world coordinates. These scale factors depend on the process use to create the landscape.