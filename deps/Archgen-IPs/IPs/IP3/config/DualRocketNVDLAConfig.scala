package chipyard

import org.chipsalliance.cde.config.Config

/** Two IP1 Rocket tiles with the pinned small NVDLA system-bus master.
  * Keep the upstream default behavioral RAM models: its alternative synth
  * wrappers require implementation-specific nv_ram_*_logic providers.
  */
class DualRocketNVDLAConfig extends Config(
  new nvidia.blocks.dla.WithNVDLA("small", synthRAMs = false) ++
  new freechips.rocketchip.rocket.WithNHugeCores(2) ++
  new chipyard.config.AbstractConfig)
