with w1 as (
    select id, max(transact_id) as transact_id
    from orders group by id),
w2 as (
    select max(transact_id) as transact_id,id
    from stop group by id),
w3 as ( 
    select max(transact_id) as transact_id,id
    from movement_order group by id ),
w4 as (
    select max(transact_id) as transact_id, id 
    from movement group by id )
 
 select m.id as movement_id, s2.actual_arrival, m.brokerage_status, m.status, o.id as order_id
 from movement m join w4 on m.id=w4.id and m.transact_id=w4.transact_id 
 left join(select so.* from stop so join w2 on so.id=w2.id and so.transact_id=w2.transact_id )  s2 on s2.id = m.dest_stop_id
 left join (select * from movement_order mo join w3 on mo.id=w3.id and mo.transact_id=w3.transact_id) mo on mo.movement_id = m.id
 left join (select o.* from orders o join w1 on o.id=w1.id and o.transact_id=w1.transact_id) o on o.id = mo.order_id
 where m.brokerage_status = 'UNLOAD'
 	and s2.actual_arrival <= date_add('hour', -48, current_timestamp) ;