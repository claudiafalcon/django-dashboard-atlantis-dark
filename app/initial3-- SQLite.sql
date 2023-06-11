-- SQLite

delete from app_conceptocdfi where ;
delete from app_impuestoscfdi;
delete from app_impuestosconceptocfdi;
delete from app_comprobantecfdi where ;


insert into app_tablasdeisr (id,year,month,limiteinferior,limitesuperior,cuotafija,porcentajeexcedente) values('45','2023','5','0.01','3730.2','0','1.92');

-- select count(*) from app_comprobanteCFDI where fecha > date('now','start of month')  order by id desc;
--delete from app_complementoconceptocdfi where concepto_id in (select id from app_conceptocdfi where comprobante_id >= 977);
--delete from app_impuestosconceptocfdi where concepto_id in (select id from app_conceptocdfi where comprobante_id >= 977);
--delete from app_conceptocdfi where comprobante_id >= 977;
--delete from app_impuestoscdfi where comprobante_id >= 977;
-- delete from app_comprobantecfdi where id >= 977;