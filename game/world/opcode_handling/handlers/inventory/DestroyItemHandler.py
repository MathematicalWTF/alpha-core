from struct import pack, unpack

from database.realm.RealmDatabaseManager import RealmDatabaseManager
from network.packet.PacketWriter import *
from utils.constants.ItemCodes import InventorySlots, InventoryError
from utils.constants.ObjectCodes import UpdateTypes


class DestroyItemHandler(object):

    @staticmethod
    def handle(world_session, socket, reader):
        if len(reader.data) >= 3:  # Avoid handling empty destroy item packet
            bag, source_slot, count = unpack('<3B', reader.data[:3])
            if bag == 0xFF or bag == InventorySlots.SLOT_BANK_END:
                bag = InventorySlots.SLOT_INBACKPACK.value

            item = world_session.player_mgr.inventory.get_item(bag, source_slot)
            if item:
                if item.is_container() and not item.is_empty():
                    world_session.player_mgr.inventory.send_equip_error(
                        InventoryError.BAG_NOT_EMPTY, item)
                else:
                    RealmDatabaseManager.character_inventory_delete(item.item_instance)
                    world_session.player_mgr.inventory.mark_as_removed(item)
                    world_session.player_mgr.session.request.sendall(item.get_destroy_packet())

                    if world_session.player_mgr.inventory.is_bag_pos(source_slot):
                        world_session.player_mgr.inventory.remove_bag(source_slot)
                    else:
                        container = world_session.player_mgr.inventory.get_container(bag)
                        if container:
                            container.remove_item_in_slot(source_slot)

                    if world_session.player_mgr.inventory.is_equipment_pos(bag, source_slot):
                        world_session.player_mgr.set_dirty(dirty_inventory=True)
                    else:
                        world_session.player_mgr.send_update_self()

        return 0
