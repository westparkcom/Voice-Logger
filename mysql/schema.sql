-- MySQL dump 10.13  Distrib 5.5.49, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: logger
-- ------------------------------------------------------
-- Server version	5.5.49-0+deb8u1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `CallLoggerStats`
--

DROP TABLE IF EXISTS `CallLoggerStats`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `CallLoggerStats` (
  `id` int(20) NOT NULL AUTO_INCREMENT,
  `Station` int(12) NOT NULL DEFAULT '9999',
  `ClientID` varchar(18) NOT NULL,
  `InboundFlag` varchar(1) NOT NULL DEFAULT 'I',
  `DNIS` varchar(20) DEFAULT NULL,
  `ANI` varchar(20) DEFAULT NULL,
  `CSN` varchar(18) DEFAULT NULL,
  `AgentLoginID` varchar(8) DEFAULT NULL,
  `AudioFilePath` varchar(255) NOT NULL DEFAULT '/usr/share/freeswitch/sounds/recordings/null.mp3',
  `LoggerDate` datetime NOT NULL,
  `AccessTime` float NOT NULL,
  `UniqueID` varchar(60) NOT NULL,
  `Paused` tinyint(4) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `Station` (`Station`),
  KEY `ClientID` (`ClientID`),
  KEY `InboundFlag` (`InboundFlag`),
  KEY `DNIS` (`DNIS`),
  KEY `ANI` (`ANI`),
  KEY `CSN` (`CSN`),
  KEY `AgentLoginID` (`AgentLoginID`),
  KEY `LoggerDate` (`LoggerDate`),
  KEY `AccessTime` (`AccessTime`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-10-17 13:30:09
